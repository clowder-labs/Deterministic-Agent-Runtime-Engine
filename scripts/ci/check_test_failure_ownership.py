#!/usr/bin/env python3
"""Test failure ownership attribution report.

Reads pytest output (from stdin, a file, or a fresh run) and emits a
structured report that groups each failure by its responsible module.

Usage::

    # Run pytest internally and report
    python scripts/ci/check_test_failure_ownership.py

    # Read from an existing report file
    python scripts/ci/check_test_failure_ownership.py --report results.txt

    # Pipe pytest output via stdin
    pytest -q --tb=line tests/ | python scripts/ci/check_test_failure_ownership.py --stdin
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Ensure repo root is importable so ``from scripts.ci.test_ownership_map``
# works regardless of how the script is invoked.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

FAILED_TEST_RE = re.compile(r"^FAILED\s+(.+?)(?=\s+-\s+|$)")
ERROR_TEST_RE = re.compile(r"^ERROR\s+(.+?)(?=\s+-\s+|$)")


def _looks_like_test_nodeid(token: str) -> bool:
    """Return true when a pytest summary token looks like a real test node id."""
    # ``ERROR path/to/test_file.py`` is still a file-level collection/import failure.
    # Only ``.py::...`` tokens identify a concrete pytest test node.
    return ".py::" in token


def _summary_nodeid(line: str, pattern: re.Pattern[str]) -> str | None:
    """Extract the pytest summary nodeid portion from a FAILED/ERROR line."""
    match = pattern.match(line)
    if match is None:
        return None
    return match.group(1)


def _parse_failed_lines(text: str) -> list[str]:
    """Extract ``FAILED``/``ERROR`` test node IDs from raw pytest output."""
    results: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        failed_nodeid = _summary_nodeid(stripped, FAILED_TEST_RE)
        if failed_nodeid is not None:
            results.append(failed_nodeid)
            continue
        error_nodeid = _summary_nodeid(stripped, ERROR_TEST_RE)
        if error_nodeid is not None and _looks_like_test_nodeid(error_nodeid):
            results.append(error_nodeid)
    return results


def _has_unattributed_pytest_error(text: str) -> bool:
    """Detect pytest process failures that did not yield attributable node IDs."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        normalized = stripped.lower()
        if stripped.startswith(("ERROR:", "ERROR collecting ", "INTERNALERROR>")):
            return True
        if "KeyboardInterrupt" in stripped or "NO_TESTS_COLLECTED" in stripped:
            return True
        if normalized.startswith("no tests ran") or "no tests collected" in normalized:
            return True
        error_nodeid = _summary_nodeid(stripped, ERROR_TEST_RE)
        if error_nodeid is not None and not _looks_like_test_nodeid(error_nodeid):
            return True
    return False


def _test_path_from_nodeid(nodeid: str) -> str:
    """Convert ``tests/unit/test_foo.py::test_bar`` to ``tests/unit/test_foo.py``."""
    return nodeid.split("::")[0]


def _build_report(failed_nodeids: list[str]) -> str:
    from scripts.ci.test_ownership_map import OWNERSHIP_MAP

    if not failed_nodeids:
        return "=== Test Failure Ownership Report ===\n\nNo test failures detected.\n"

    # Group by module
    module_groups: dict[str, list[str]] = {}
    unmapped: list[str] = []

    for nodeid in failed_nodeids:
        path = _test_path_from_nodeid(nodeid)
        entry = OWNERSHIP_MAP.get(path)
        if entry:
            module_groups.setdefault(entry["module"], []).append(nodeid)
        else:
            unmapped.append(nodeid)

    lines: list[str] = ["=== Test Failure Ownership Report ===", ""]

    for module in sorted(module_groups):
        # Find owner from first entry in this module group
        first_path = _test_path_from_nodeid(module_groups[module][0])
        entry = OWNERSHIP_MAP.get(first_path, {})
        owner = entry.get("owner") or "unassigned"
        lines.append(f"Module: {module} (owner: {owner})")
        for nodeid in sorted(module_groups[module]):
            lines.append(f"  FAILED {nodeid}")
        lines.append("")

    lines.append("UNMAPPED (no ownership entry):")
    if unmapped:
        for nodeid in sorted(unmapped):
            lines.append(f"  FAILED {nodeid}")
    else:
        lines.append("  (none)")
    lines.append("")

    total_failed = len(failed_nodeids)
    total_modules = len(module_groups) + (1 if unmapped else 0)
    lines.append(f"Summary: {total_failed} failed tests across {total_modules} modules")
    return "\n".join(lines)


def _format_completed_output(completed: subprocess.CompletedProcess[str]) -> str:
    """Join stdout/stderr into the single text blob consumed by the parser."""
    return "\n".join(
        part for part in [completed.stdout.strip(), completed.stderr.strip()] if part
    ).strip()


def _run_pytest() -> subprocess.CompletedProcess[str]:
    """Run ``pytest -q --tb=line tests/`` and return the completed process."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", "tests/"],
        capture_output=True,
        text=True,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test failure ownership attribution report")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--stdin",
        action="store_true",
        help="Read pytest output from stdin",
    )
    source.add_argument(
        "--report",
        type=Path,
        metavar="FILE",
        help="Read pytest output from a file",
    )
    args = parser.parse_args(argv)

    if args.stdin:
        raw = sys.stdin.read()
        pytest_returncode: int | None = None
    elif args.report:
        raw = args.report.read_text(encoding="utf-8")
        pytest_returncode = None
    else:
        completed = _run_pytest()
        raw = _format_completed_output(completed)
        pytest_returncode = completed.returncode

    failed = _parse_failed_lines(raw)
    fallback_exit_code = pytest_returncode
    if fallback_exit_code is None and not failed and _has_unattributed_pytest_error(raw):
        fallback_exit_code = 1
    if fallback_exit_code and not failed:
        if raw:
            print(raw, file=sys.stderr)
        return fallback_exit_code

    report = _build_report(failed)
    print(report)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
