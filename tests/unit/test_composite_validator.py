import pytest

from dare_framework.components.validator import CompositeValidator
from dare_framework.components.base_component import BaseComponent
from dare_framework.core.interfaces import IValidator
from dare_framework.core.models import (
    Milestone,
    ProposedStep,
    RunContext,
    ValidationResult,
    VerifyResult,
    new_id,
)


class FailingValidator(BaseComponent, IValidator):
    def __init__(self, order: int, errors: list[str]):
        self._order = order
        self._errors = errors

    @property
    def order(self) -> int:
        return self._order

    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        return ValidationResult(success=False, errors=self._errors)

    async def validate_milestone(self, milestone: Milestone, result, ctx: RunContext) -> VerifyResult:
        return VerifyResult(success=False, errors=self._errors, evidence=[])

    async def validate_evidence(self, evidence, predicate) -> bool:
        return False


@pytest.mark.asyncio
async def test_composite_validator_aggregates_errors_in_order():
    validator_low = FailingValidator(order=10, errors=["low"])
    validator_high = FailingValidator(order=50, errors=["high"])
    composite = CompositeValidator([validator_high, validator_low])

    result = await composite.validate_plan(
        [ProposedStep(step_id=new_id("step"), tool_name="noop", tool_input={})],
        RunContext(deps=None, run_id="run"),
    )

    assert result.success is False
    assert result.errors == ["low", "high"]


@pytest.mark.asyncio
async def test_composite_validator_collects_verify_errors():
    validator_a = FailingValidator(order=20, errors=["a"])
    validator_b = FailingValidator(order=10, errors=["b"])
    composite = CompositeValidator([validator_a, validator_b])

    result = await composite.validate_milestone(
        Milestone(milestone_id="m1", description="desc", user_input="input"),
        result=object(),
        ctx=RunContext(deps=None, run_id="run"),
    )

    assert result.success is False
    assert result.errors == ["b", "a"]
