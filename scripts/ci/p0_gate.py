#!/usr/bin/env python3
"""Run the P0 conformance gate and emit a deterministic summary."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FAILED_TEST_RE = re.compile(r"^FAILED\s+([^\s]+)")


@dataclass(frozen=True, slots=True)
class CategorySpec:
    label: str
    tests: list[str]
    modules: list[str]
    action: str


@dataclass(frozen=True, slots=True)
class CategoryResult:
    spec: CategorySpec
    passed: bool
    failed_tests: list[str]
    raw_output: str


DEFAULT_CATEGORY_SPECS: tuple[CategorySpec, ...] = (
    CategorySpec(
        label="SECURITY_REGRESSION",
        tests=[
            "tests/integration/test_security_policy_gate_flow.py",
            "tests/unit/test_dare_agent_security_policy_gate.py",
            "tests/unit/test_dare_agent_security_boundary.py",
            "tests/unit/test_transport_adapters.py",
            "tests/unit/test_examples_cli.py",
            "tests/unit/test_examples_cli_mcp.py",
        ],
        modules=[
            "dare_framework/security",
            "dare_framework/tool/_internal/governed_tool_gateway.py",
            "dare_framework/transport/_internal/adapters.py",
            "examples/05-dare-coding-agent-enhanced/cli.py",
            "examples/06-dare-coding-agent-mcp/cli.py",
        ],
        action="inspect trust/policy/approval flow before tool invocation",
    ),
    CategorySpec(
        label="STEP_EXEC_REGRESSION",
        tests=[
            "tests/integration/test_p0_conformance_gate.py::test_step_driven_session_executes_validated_steps_in_order",
            "tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step",
            "tests/unit/test_dare_agent_step_driven_mode.py",
        ],
        modules=[
            "dare_framework/agent/dare_agent.py",
            "dare_framework/agent/_internal/execute_engine.py",
            "dare_framework/plan",
        ],
        action="inspect step execution order, fail-fast handling, and validated-plan routing",
    ),
    CategorySpec(
        label="AUDIT_CHAIN_REGRESSION",
        tests=[
            "tests/integration/test_p0_conformance_gate.py::test_default_event_log_replay_and_hash_chain_hold_for_runtime_session",
            "tests/unit/test_event_sqlite_event_log.py",
            "tests/unit/test_builder_security_boundary.py::test_default_event_log_replay_returns_ordered_session_window",
        ],
        modules=[
            "dare_framework/event/_internal/sqlite_event_log.py",
            "dare_framework/event/kernel.py",
            "dare_framework/observability/_internal/event_trace_bridge.py",
            "dare_framework/agent/builder.py",
        ],
        action="inspect SQLite event append/hash-chain/replay wiring and trace-aware event-log bridging",
    ),
)


def extract_failed_tests(output: str) -> list[str]:
    failed_tests: list[str] = []
    for line in output.splitlines():
        match = FAILED_TEST_RE.match(line.strip())
        if match:
            failed_tests.append(match.group(1))
    return failed_tests


def format_summary(results: list[CategoryResult]) -> str:
    passed = all(result.passed for result in results)
    lines = [f"p0-gate: {'PASS' if passed else 'FAIL'}"]
    for result in results:
        if result.passed:
            lines.append(f"- {result.spec.label}: 0 failures")
            continue
        failed_tests = ", ".join(result.failed_tests or ["<no failing test ids captured>"])
        modules = ", ".join(result.spec.modules)
        lines.extend(
            [
                f"- {result.spec.label}",
                f"  tests: {failed_tests}",
                f"  modules: {modules}",
                f"  action: {result.spec.action}",
            ]
        )
    return "\n".join(lines)


def run_category(spec: CategorySpec) -> CategoryResult:
    command = [sys.executable, "-m", "pytest", "-q", *spec.tests]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    raw_output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part).strip()
    return CategoryResult(
        spec=spec,
        passed=completed.returncode == 0,
        failed_tests=extract_failed_tests(raw_output),
        raw_output=raw_output,
    )


def _write_step_summary(summary: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as fh:
        fh.write("## p0-gate\n\n")
        fh.write("```text\n")
        fh.write(summary)
        fh.write("\n```\n")


def main() -> int:
    results = [run_category(spec) for spec in DEFAULT_CATEGORY_SPECS]

    for result in results:
        if result.passed or not result.raw_output:
            continue
        print(f"== {result.spec.label} raw output ==", file=sys.stderr)
        print(result.raw_output, file=sys.stderr)

    summary = format_summary(results)
    print(summary)
    _write_step_summary(summary)
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
