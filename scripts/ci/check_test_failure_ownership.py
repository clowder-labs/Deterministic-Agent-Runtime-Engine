#!/usr/bin/env python3
"""Validate failure-test ownership mapping used by the P0 gate."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    # Allow direct execution: `python scripts/ci/check_test_failure_ownership.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.p0_gate import DEFAULT_CATEGORY_SPECS, CategorySpec


def _normalize_selector_segments(selector: str) -> list[str]:
    segments = [segment.strip() for segment in selector.split("::")]
    normalized: list[str] = []
    for segment in segments:
        if not segment:
            continue
        # `pytest` parametrization suffixes (`test_x[param]`) are narrower matches
        # than the base node (`test_x`) and should count as overlapping selectors.
        normalized.append(segment.split("[", 1)[0])
    return normalized


def _selectors_overlap(left: str, right: str) -> bool:
    left_segments = _normalize_selector_segments(left)
    right_segments = _normalize_selector_segments(right)
    if not left_segments or not right_segments:
        return False

    def _is_prefix(prefix: list[str], full: list[str]) -> bool:
        if len(prefix) > len(full):
            return False
        return prefix == full[: len(prefix)]

    return _is_prefix(left_segments, right_segments) or _is_prefix(right_segments, left_segments)


def validate_category_specs(specs: list[CategorySpec]) -> list[str]:
    """Return validation issues for failure ownership mapping specs."""
    issues: list[str] = []
    test_to_label: dict[str, str] = {}
    selector_mappings: list[tuple[str, str]] = []

    for spec in specs:
        if not spec.tests:
            issues.append(f"{spec.label}: missing test selectors")
        if not spec.modules:
            issues.append(f"{spec.label}: missing module ownership scope")

        owner = spec.owner.strip()
        if not owner:
            issues.append(f"{spec.label}: missing owner")
        elif not owner.startswith("@"):
            issues.append(f"{spec.label}: owner must be a GitHub handle (starts with '@')")

        for selector in spec.tests:
            normalized = selector.strip()
            if not normalized:
                issues.append(f"{spec.label}: empty test selector")
                continue

            existing = test_to_label.get(normalized)
            if existing and existing != spec.label:
                issues.append(
                    "duplicate test selector mapping: "
                    f"{normalized} is mapped by both {existing} and {spec.label}"
                )
                continue

            for mapped_selector, mapped_label in selector_mappings:
                if mapped_label == spec.label:
                    continue
                if _selectors_overlap(normalized, mapped_selector):
                    issues.append(
                        "overlapping test selector mapping: "
                        f"{normalized} ({spec.label}) overlaps with "
                        f"{mapped_selector} ({mapped_label})"
                    )
                    break

            test_to_label[normalized] = spec.label
            selector_mappings.append((normalized, spec.label))

    return issues


def main() -> int:
    specs = list(DEFAULT_CATEGORY_SPECS)
    issues = validate_category_specs(specs)

    if issues:
        print("[failure-ownership] failed")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("[failure-ownership] passed")
    for spec in specs:
        print(f"- {spec.label}: owner={spec.owner}; tests={len(spec.tests)}; modules={len(spec.modules)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
