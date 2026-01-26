from __future__ import annotations

from dare_framework.plan.planning import ProposedPlan, ValidatedPlan
from dare_framework.plan.results import ExecuteResult, VerifyResult
from dare_framework.plan.components import IValidator
from dare_framework.contracts import ComponentType
from dare_framework.builder.base_component import ConfigurableComponent


class CompositeValidator(ConfigurableComponent, IValidator):
    """Aggregate multiple validators into a single v2 validator.

    Notes on semantics:
    - `validate_plan()` uses the first validator's `ValidatedPlan` as the "base"
      validated plan (typically `GatewayValidator`), while still collecting errors
      from all validators for explainability.
    - `verify_milestone()` always runs all validators (ordered by `order`) and
      aggregates errors and evidence.
    """

    component_type = ComponentType.VALIDATOR

    def __init__(self, validators: list[IValidator]) -> None:
        self._validators = list(validators)

    def _ordered(self) -> list[IValidator]:
        return sorted(self._validators, key=lambda validator: getattr(validator, "order", 100))

    async def validate_plan(self, plan: ProposedPlan, ctx: dict) -> ValidatedPlan:
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
            base_plan = ValidatedPlan(plan_description=plan.plan_description, steps=[], success=True, errors=[])
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

    async def verify_milestone(self, result: ExecuteResult, ctx: dict) -> VerifyResult:
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
