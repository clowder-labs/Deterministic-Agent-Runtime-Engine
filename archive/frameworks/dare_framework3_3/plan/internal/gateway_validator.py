"""Gateway validator implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework3_3.plan.component import IValidator
from dare_framework3_3.plan.types import (
    ProposedPlan,
    ValidatedPlan,
    ValidatedStep,
    ExecuteResult,
    VerifyResult,
    Envelope,
)
from dare_framework3_3.security.types import RiskLevel

if TYPE_CHECKING:
    from dare_framework3_3.tool.kernel import IToolGateway
    from dare_framework3_3.tool.types import CapabilityDescriptor
    from dare_framework3_3.context.types import Budget


class GatewayValidator(IValidator):
    """Validator that derives trusted fields from the tool gateway registry.
    
    This is the primary validator that ensures:
    1. All referenced capabilities exist in the registry
    2. Risk levels are derived from trusted registry metadata
    3. Envelopes are properly configured
    
    Args:
        tool_gateway: The tool gateway to validate capabilities against
    """

    def __init__(self, tool_gateway: "IToolGateway") -> None:
        self._tool_gateway = tool_gateway

    async def validate_plan(
        self,
        plan: ProposedPlan,
        ctx: dict[str, Any],
    ) -> ValidatedPlan:
        """Validate a proposed plan against the capability registry."""
        if not plan.steps:
            return ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=False,
                errors=["plan has no steps"],
            )

        # Build capability index from gateway
        capability_index = {
            cap.id: cap
            for cap in await self._tool_gateway.list_capabilities()
        }
        
        steps: list[ValidatedStep] = []
        errors: list[str] = []

        for step in plan.steps:
            # Handle plan tools specially (they don't need registry lookup)
            if step.capability_id.startswith("plan:"):
                steps.append(
                    ValidatedStep(
                        step_id=step.step_id,
                        capability_id=step.capability_id,
                        risk_level=RiskLevel.READ_ONLY,
                        params=dict(step.params),
                        description=step.description,
                        envelope=_derive_envelope(
                            step.capability_id,
                            step.envelope,
                            RiskLevel.READ_ONLY,
                        ),
                    )
                )
                continue

            # Look up capability in registry
            capability = capability_index.get(step.capability_id)
            if capability is None:
                errors.append(f"unknown capability: {step.capability_id}")
                continue

            # Derive risk level from trusted registry
            risk_level = _parse_risk_level(
                (capability.metadata or {}).get("risk_level")
            )
            
            steps.append(
                ValidatedStep(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    risk_level=risk_level,
                    params=dict(step.params),
                    description=step.description,
                    envelope=_derive_envelope(
                        step.capability_id,
                        step.envelope,
                        risk_level,
                        capability,
                    ),
                )
            )

        if errors:
            return ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=False,
                errors=errors,
            )

        return ValidatedPlan(
            plan_description=plan.plan_description,
            steps=steps,
            success=True,
            errors=[],
        )

    async def verify_milestone(
        self,
        result: ExecuteResult,
        ctx: dict[str, Any],
    ) -> VerifyResult:
        """Verify milestone based on execution result."""
        if result.success:
            return VerifyResult(success=True, errors=[], evidence=[])
        return VerifyResult(success=False, errors=list(result.errors), evidence=[])


def _derive_envelope(
    capability_id: str,
    envelope: Envelope | None,
    risk_level: RiskLevel,
    capability: "CapabilityDescriptor | None" = None,
) -> Envelope:
    """Derive a properly configured envelope for a step."""
    from dare_framework3_3.context.types import Budget
    
    if envelope is None:
        envelope = Envelope()

    # Determine max tool calls based on capability type
    max_tool_calls = envelope.budget.max_tool_calls
    if max_tool_calls is None:
        is_work_unit = bool(
            (capability.metadata or {}).get("is_work_unit", False)
            if capability else False
        )
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
    """Parse a risk level from various input types."""
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return RiskLevel.READ_ONLY
    return RiskLevel.READ_ONLY
