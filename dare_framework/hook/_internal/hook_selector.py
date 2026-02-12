"""Selector utilities for deterministic hook ordering and filtering."""

from __future__ import annotations

from typing import Any

_SOURCE_RANK = {"system": 0, "config": 1, "code": 2}
_LANE_RANK = {"control": 0, "observe": 1}


def sort_hook_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort hooks by deterministic governance precedence."""

    return sorted(
        specs,
        key=lambda spec: (
            str(spec.get("phase", "")),
            _LANE_RANK.get(str(spec.get("lane", "observe")), 99),
            int(spec.get("priority", 100)),
            _SOURCE_RANK.get(str(spec.get("source", "code")), 99),
            int(spec.get("registration_order", 0)),
        ),
    )


def filter_hook_specs(
    specs: list[dict[str, Any]],
    *,
    phase: str | None = None,
) -> list[dict[str, Any]]:
    """Filter hook specs by phase when requested."""

    if phase is None:
        return list(specs)
    return [spec for spec in specs if str(spec.get("phase")) == phase]


def deduplicate_hook_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate hook specs by explicit dedup key, preserving first occurrence."""

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in specs:
        dedup_key = spec.get("dedup_key")
        if dedup_key is None:
            deduped.append(spec)
            continue
        key = str(dedup_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)
    return deduped


__all__ = ["deduplicate_hook_specs", "filter_hook_specs", "sort_hook_specs"]
