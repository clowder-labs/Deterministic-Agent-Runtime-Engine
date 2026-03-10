import pytest

pytest.skip(
    "Legacy validator implementations are archived; port to canonical dare_framework "
    "once composite validator support exists.",
    allow_module_level=True,
)

from dare_framework.plan.impl.validators.composite import CompositeValidator
from dare_framework.builder.base_component import ConfigurableComponent
from dare_framework.contracts.ids import generator_id
from dare_framework.plan.planning import ProposedPlan, ProposedStep, ValidatedPlan
from dare_framework.plan.results import ExecuteResult, VerifyResult
from dare_framework.plan.components import IValidator
from dare_framework.contracts import ComponentType


class FailingValidator(ConfigurableComponent, IValidator):
    component_type = ComponentType.VALIDATOR

    def __init__(self, order: int, errors: list[str]) -> None:
        self._order = order
        self._errors = errors

    @property
    def order(self) -> int:
        return self._order

    async def validate_plan(self, plan: ProposedPlan, ctx: dict) -> ValidatedPlan:
        return ValidatedPlan(plan_description=plan.plan_description, steps=[], success=False, errors=self._errors)

    async def verify_milestone(
        self,
        result: ExecuteResult,
        ctx: dict,
        *,
        plan: ValidatedPlan | None = None,
    ) -> VerifyResult:
        _ = plan
        return VerifyResult(success=False, errors=self._errors, evidence=[])


@pytest.mark.asyncio
async def test_composite_validator_aggregates_errors_in_order():
    validator_low = FailingValidator(order=10, errors=["low"])
    validator_high = FailingValidator(order=50, errors=["high"])
    composite = CompositeValidator([validator_high, validator_low])

    plan = ProposedPlan(
        plan_description="noop",
        steps=[ProposedStep(step_id=generator_id("step"), capability_id="tool:noop", params={})],
    )
    result = await composite.validate_plan(plan, {})

    assert result.success is False
    assert result.errors == ["low", "high"]


@pytest.mark.asyncio
async def test_composite_validator_collects_verify_errors():
    validator_a = FailingValidator(order=20, errors=["a"])
    validator_b = FailingValidator(order=10, errors=["b"])
    composite = CompositeValidator([validator_a, validator_b])

    result = await composite.verify_milestone(ExecuteResult(success=False, errors=["failed"]), {})

    assert result.success is False
    assert result.errors == ["b", "a"]
