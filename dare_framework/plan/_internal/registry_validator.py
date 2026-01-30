"""Validator that derives trusted plan metadata from the capability registry."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from dare_framework.infra.component import ComponentType
from dare_framework.plan.interfaces import IValidator
from dare_framework.plan.types import (
    Envelope,
    ProposedPlan,
    ProposedStep,
    RunResult,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
)
from dare_framework.security.types import RiskLevel
from dare_framework.tool.types import CapabilityKind, CapabilityMetadata

if TYPE_CHECKING:
    from dare_framework.tool.kernel import IToolGateway
    from dare_framework.tool.interfaces import IToolManager
    from dare_framework.tool.types import CapabilityDescriptor


class RegistryPlanValidator(IValidator):
    """Validate plans using trusted capability registry metadata.

    This validator:
    - Confirms referenced capabilities exist in the registry
    - Derives risk level and trusted metadata from registry entries
    - Overrides any planner-provided security fields
    """

    def __init__(
        self,
        *,
        tool_gateway: "IToolGateway | None" = None,
        tool_manager: "IToolManager | None" = None,
        name: str = "registry_plan_validator",
    ) -> None:
        if tool_gateway is None and tool_manager is None:
            raise ValueError("RegistryPlanValidator requires a tool gateway or tool manager")
        self._tool_gateway = tool_gateway
        self._tool_manager = tool_manager
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.VALIDATOR

    async def validate_plan(self, plan: ProposedPlan, ctx: Any) -> ValidatedPlan:
        capability_index = await self._capability_index()
        errors: list[str] = []
        validated_steps: list[ValidatedStep] = []

        for step in plan.steps:
            validated = self._validate_step(step, capability_index, errors)
            if validated is not None:
                validated_steps.append(validated)

        if errors:
            return ValidatedPlan(
                plan_description=plan.plan_description,
                steps=[],
                success=False,
                errors=errors,
            )

        return ValidatedPlan(
            plan_description=plan.plan_description,
            steps=validated_steps,
            success=True,
            errors=[],
        )

    async def verify_milestone(self, result: RunResult, ctx: Any) -> VerifyResult:
        if result.success:
            return VerifyResult(success=True, errors=[], metadata={})
        return VerifyResult(success=False, errors=list(result.errors), metadata={})

    async def _capability_index(self) -> dict[str, "CapabilityDescriptor"]:
        capabilities: list[CapabilityDescriptor] = []
        if self._tool_gateway is not None:
            capabilities = list(await self._tool_gateway.list_capabilities())
        elif self._tool_manager is not None:
            capabilities = list(self._tool_manager.list_capabilities())

        index: dict[str, CapabilityDescriptor] = {}
        for capability in capabilities:
            index[capability.id] = capability
            index.setdefault(capability.name, capability)
        return index

    def _validate_step(
        self,
        step: ProposedStep,
        capability_index: dict[str, "CapabilityDescriptor"],
        errors: list[str],
    ) -> ValidatedStep | None:
        if step.capability_id.startswith("plan:"):
            risk_level = RiskLevel.READ_ONLY
            metadata = {"capability_kind": CapabilityKind.PLAN_TOOL.value}
            return ValidatedStep(
                step_id=step.step_id,
                capability_id=step.capability_id,
                risk_level=risk_level,
                params=dict(step.params),
                description=step.description,
                envelope=_derive_envelope(step.envelope, step.capability_id, risk_level),
                metadata=metadata,
            )

        capability = capability_index.get(step.capability_id)
        if capability is None:
            errors.append(f"unknown capability: {step.capability_id}")
            return None

        metadata = _normalize_metadata(capability.metadata)
        risk_level = _parse_risk_level(metadata.get("risk_level"))

        return ValidatedStep(
            step_id=step.step_id,
            capability_id=step.capability_id,
            risk_level=risk_level,
            params=dict(step.params),
            description=step.description,
            envelope=_derive_envelope(step.envelope, step.capability_id, risk_level),
            metadata=metadata,
        )


def _derive_envelope(
    envelope: Envelope | None,
    capability_id: str,
    risk_level: RiskLevel,
) -> Envelope:
    if envelope is None:
        return Envelope(
            allowed_capability_ids=[capability_id],
            risk_level=risk_level,
        )

    allowlist = envelope.allowed_capability_ids or [capability_id]
    return Envelope(
        allowed_capability_ids=list(allowlist),
        budget=envelope.budget,
        done_predicate=envelope.done_predicate,
        risk_level=risk_level,
    )


def _normalize_metadata(metadata: CapabilityMetadata | None) -> dict[str, Any]:
    if not metadata:
        return {}
    normalized: dict[str, Any] = {}
    for key, value in dict(metadata).items():
        normalized[key] = _normalize_value(value)
    return normalized


def _normalize_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _parse_risk_level(value: Any) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return RiskLevel.READ_ONLY
    return RiskLevel.READ_ONLY


__all__ = ["RegistryPlanValidator"]
