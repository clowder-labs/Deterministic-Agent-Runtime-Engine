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
    from dare_framework.tool.kernel import IToolManager
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
        tool_gateway: IToolGateway | None = None,
        tool_manager: IToolManager | None = None,
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
        capability_index, alias_index = await self._capability_index()
        errors: list[str] = []
        validated_steps: list[ValidatedStep] = []

        for step in plan.steps:
            validated = self._validate_step(step, capability_index, alias_index, errors)
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

    async def verify_milestone(
        self,
        result: RunResult,
        ctx: Any,
        *,
        plan: ValidatedPlan | None = None,
    ) -> VerifyResult:
        if result.success:
            return VerifyResult(success=True, errors=[], metadata={})
        return VerifyResult(success=False, errors=list(result.errors), metadata={})

    async def _capability_index(
        self,
    ) -> tuple[dict[str, CapabilityDescriptor], dict[str, list[CapabilityDescriptor]]]:
        capabilities: list[CapabilityDescriptor] = []
        if self._tool_gateway is not None:
            capabilities = list(self._tool_gateway.list_capabilities())
        elif self._tool_manager is not None:
            capabilities = list(self._tool_manager.list_capabilities())

        by_id: dict[str, CapabilityDescriptor] = {}
        by_alias: dict[str, list[CapabilityDescriptor]] = {}
        for capability in capabilities:
            by_id[capability.id] = capability
            _add_alias(by_alias, capability.name, capability)
            display_name = None
            if capability.metadata:
                display_name = capability.metadata.get("display_name")
            if isinstance(display_name, str) and display_name:
                _add_alias(by_alias, display_name, capability)
        return by_id, by_alias

    def _validate_step(
        self,
        step: ProposedStep,
        capability_index: dict[str, CapabilityDescriptor],
        alias_index: dict[str, list[CapabilityDescriptor]],
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

        resolved_id, capability = _resolve_capability(step.capability_id, capability_index, alias_index, errors)
        if capability is None:
            return None

        metadata = _normalize_metadata(capability.metadata)
        if "risk_level" not in metadata:
            errors.append(f"missing trusted risk metadata for capability: {resolved_id}")
            return None
        risk_level = _parse_risk_level(metadata.get("risk_level"))
        if risk_level is None:
            errors.append(f"invalid trusted risk metadata for capability: {resolved_id}")
            return None

        return ValidatedStep(
            step_id=step.step_id,
            capability_id=resolved_id,
            risk_level=risk_level,
            params=dict(step.params),
            description=step.description,
            envelope=_derive_envelope(step.envelope, resolved_id, risk_level),
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


def _add_alias(
    alias_index: dict[str, list[CapabilityDescriptor]],
    alias: str,
    capability: CapabilityDescriptor,
) -> None:
    if not alias:
        return
    alias_index.setdefault(alias, []).append(capability)


def _resolve_capability(
    raw_id: str,
    capability_index: dict[str, CapabilityDescriptor],
    alias_index: dict[str, list[CapabilityDescriptor]],
    errors: list[str],
) -> tuple[str, CapabilityDescriptor | None]:
    capability = capability_index.get(raw_id)
    if capability is not None:
        return capability.id, capability
    matches = alias_index.get(raw_id, [])
    if not matches:
        errors.append(f"unknown capability: {raw_id}")
        return raw_id, None
    if len(matches) > 1:
        match_ids = sorted({match.id for match in matches})
        errors.append(f"ambiguous capability name '{raw_id}': matches {match_ids}")
        return raw_id, None
    resolved = matches[0]
    return resolved.id, resolved


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


def _parse_risk_level(value: Any) -> RiskLevel | None:
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return None
    return None


__all__ = ["RegistryPlanValidator"]
