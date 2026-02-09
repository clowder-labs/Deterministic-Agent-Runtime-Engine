"""Composite validator implementation.

The public runtime surface expects a single `IValidator | None`. Builders allow
multi-load semantics for validators (explicit + manager-loaded), so this helper
combines multiple validators into one deterministic wrapper.
"""

from __future__ import annotations

from typing import Any

from dare_framework.plan.interfaces import IValidator


class CompositeValidator(IValidator):
    """Run validators in order and stop early on failure."""

    @property
    def name(self) -> str:
        return "composite-validator"

    def __init__(self, validators: list[IValidator]) -> None:
        self._validators = list(validators)

    async def validate_plan(self, plan: Any, ctx: Any) -> Any:
        current = plan
        for validator in self._validators:
            current = await validator.validate_plan(current, ctx)
            if not getattr(current, "success", True):
                return current
        return current

    async def verify_milestone(
            self, result: Any, ctx: Any, *, plan: Any = None
    ) -> Any:
        last = None
        for validator in self._validators:
            last = await validator.verify_milestone(result, ctx, plan=plan)
            if not getattr(last, "success", True):
                return last
        return last


__all__ = ["CompositeValidator"]
