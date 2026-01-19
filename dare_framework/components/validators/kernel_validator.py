from __future__ import annotations

from dare_framework.contracts.risk import RiskLevel
from dare_framework.core.budget import Budget
from dare_framework.core.plan.envelope import Envelope
from dare_framework.core.plan.planning import ProposedPlan, ValidatedPlan, ValidatedStep
from dare_framework.core.plan.results import ExecuteResult, VerifyResult
from dare_framework.core.protocols import IValidator
from dare_framework.core.tool.capabilities import CapabilityDescriptor
from dare_framework.core.tool.tool_gateway import IToolGateway


class GatewayValidator(IValidator):
    """Validator that derives trusted fields from the tool gateway registry (v2.0)."""

    def __init__(self, tool_gateway: IToolGateway) -> None:
        self._tool_gateway = tool_gateway

    async def validate_plan(self, plan: ProposedPlan, ctx: dict) -> ValidatedPlan:
        if not plan.steps:
            return ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=False,
                errors=["plan has no steps"],
            )

        capability_index = {cap.id: cap for cap in await self._tool_gateway.list_capabilities()}
        steps: list[ValidatedStep] = []
        errors: list[str] = []

        for step in plan.steps:
            if step.capability_id.startswith("plan:"):
                steps.append(
                    ValidatedStep(
                        step_id=step.step_id,
                        capability_id=step.capability_id,
                        risk_level=RiskLevel.READ_ONLY,
                        params=dict(step.params),
                        description=step.description,
                        envelope=_derive_envelope(step.capability_id, step.envelope, RiskLevel.READ_ONLY),
                    )
                )
                continue

            capability = capability_index.get(step.capability_id)
            if capability is None:
                errors.append(f"unknown capability: {step.capability_id}")
                continue

            risk_level = _parse_risk_level((capability.metadata or {}).get("risk_level"))
            steps.append(
                ValidatedStep(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    risk_level=risk_level,
                    params=dict(step.params),
                    description=step.description,
                    envelope=_derive_envelope(step.capability_id, step.envelope, risk_level, capability),
                )
            )

        if errors:
            return ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=False,
                errors=errors,
            )

        return ValidatedPlan(plan_description=plan.plan_description, steps=steps, success=True, errors=[])

    async def verify_milestone(self, result: ExecuteResult, ctx: dict) -> VerifyResult:
        if result.success:
            return VerifyResult(success=True, errors=[], evidence=[])
        return VerifyResult(success=False, errors=list(result.errors), evidence=[])


def _derive_envelope(
    capability_id: str,
    envelope: Envelope | None,
    risk_level: RiskLevel,
    capability: CapabilityDescriptor | None = None,
) -> Envelope:
    if envelope is None:
        envelope = Envelope()

    max_tool_calls = envelope.budget.max_tool_calls
    if max_tool_calls is None:
        is_work_unit = bool((capability.metadata or {}).get("is_work_unit", False)) if capability else False
        max_tool_calls = 30 if is_work_unit else 1

    return Envelope(
        allowed_capability_ids=envelope.allowed_capability_ids or [capability_id],
        budget=Budget(
            max_tokens=envelope.budget.max_tokens,
            max_cost=envelope.budget.max_cost,
            max_time_seconds=envelope.budget.max_time_seconds,
            max_tool_calls=max_tool_calls,
        ),
        done_predicate=envelope.done_predicate,
        risk_level=risk_level,
    )


def _parse_risk_level(value: object) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return RiskLevel.READ_ONLY
    return RiskLevel.READ_ONLY
