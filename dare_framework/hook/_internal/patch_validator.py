"""Patch validation utilities for governed hook mutations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PatchValidationResult:
    """Validation output for patch governance checks."""

    patch: dict[str, Any] | None = None
    error_code: str | None = None
    message: str | None = None


def merge_patches(
    patches: list[dict[str, Any] | None],
    *,
    allowlist: tuple[str, ...] | list[str],
) -> PatchValidationResult:
    """Merge hook patches while enforcing allowlist and conflict policy."""

    merged: dict[str, Any] = {}
    allowset = {str(item) for item in allowlist}
    for patch in patches:
        if not patch:
            continue
        for key, value in patch.items():
            if key not in allowset:
                return PatchValidationResult(
                    error_code="HOOK_CONTRACT_ERROR",
                    message=f"field '{key}' is not allowlisted",
                )
            if key in merged and merged[key] != value:
                return PatchValidationResult(
                    error_code="HOOK_CONTRACT_ERROR",
                    message=f"conflicting mutation for '{key}'",
                )
            merged[key] = value
    return PatchValidationResult(patch=merged)


__all__ = ["PatchValidationResult", "merge_patches"]
