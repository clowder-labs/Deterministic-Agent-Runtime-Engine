"""Composite validator implementation."""

from __future__ import annotations

from typing import Any

from dare_framework2.plan.components import IValidator
from dare_framework2.plan.types import (
    ProposedPlan,
    ValidatedPlan,
    ExecuteResult,
    VerifyResult,
)


class CompositeValidator(IValidator):
    """Aggregate multiple validators into a single validator.
    
    Semantics:
    - validate_plan(): Uses the first validator's ValidatedPlan as the "base"
      (typically GatewayValidator), while collecting errors from all validators.
    - verify_milestone(): Runs all validators (ordered by `order` attribute)
      and aggregates errors and evidence.
    
    Args:
        validators: List of validators to compose
    """

    def __init__(self, validators: list[IValidator]) -> None:
        self._validators = list(validators)

    def _ordered(self) -> list[IValidator]:
        """Return validators sorted by their order attribute."""
        return sorted(
            self._validators,
            key=lambda v: getattr(v, "order", 100),
        )

    async def validate_plan(
        self,
        plan: ProposedPlan,
        ctx: dict[str, Any],
    ) -> ValidatedPlan:
        """Validate plan using all validators."""
        if not self._validators:
            return ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=False,
                errors=["no validators configured"],
            )

        errors: list[str] = []
        base_plan: ValidatedPlan | None = None
        
        for validator in self._ordered():
            result = await validator.validate_plan(plan, ctx)
            if base_plan is None:
                base_plan = result
            if not result.success:
                errors.extend(result.errors)
        
        if base_plan is None:
            base_plan = ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=True,
                errors=[],
            )
        
        if errors:
            return ValidatedPlan(
                plan_description=base_plan.plan_description,
                steps=[],
                metadata=dict(base_plan.metadata),
                validated_at=base_plan.validated_at,
                success=False,
                errors=errors,
            )
        
        return base_plan

    async def verify_milestone(
        self,
        result: ExecuteResult,
        ctx: dict[str, Any],
    ) -> VerifyResult:
        """Verify milestone using all validators."""
        errors: list[str] = []
        evidence = []
        success = True
        
        for validator in self._ordered():
            verify_result = await validator.verify_milestone(result, ctx)
            if not verify_result.success:
                success = False
                errors.extend(verify_result.errors)
            evidence.extend(verify_result.evidence)
        
        return VerifyResult(success=success, errors=errors, evidence=evidence)
