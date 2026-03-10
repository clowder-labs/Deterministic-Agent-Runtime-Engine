"""Default security boundary implementations."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Iterable

from dare_framework.security.errors import (
    SECURITY_TRUST_DERIVATION_FAILED,
    SecurityBoundaryError,
)
from dare_framework.security.kernel import ISecurityBoundary
from dare_framework.security.types import PolicyDecision, RiskLevel, SandboxSpec, TrustedInput


def _coerce_risk_level(value: Any) -> RiskLevel | None:
    if isinstance(value, RiskLevel):
        return value
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return None
    return None


def _coerce_policy_decision(value: Any, *, default: PolicyDecision) -> PolicyDecision:
    if isinstance(value, PolicyDecision):
        return value
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, str):
        try:
            return PolicyDecision(value)
        except ValueError:
            return default
    return default


def _coerce_risk_levels(values: Any, *, default: set[RiskLevel]) -> set[RiskLevel]:
    if not isinstance(values, (list, tuple, set)):
        return set(default)
    normalized: set[RiskLevel] = set()
    for value in values:
        parsed = _coerce_risk_level(value)
        if parsed is not None:
            normalized.add(parsed)
    return normalized if normalized else set(default)


def _coerce_str_set(values: Any) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip()
        if item:
            normalized.add(item)
    return normalized


def _descriptor_metadata(context: dict[str, Any]) -> dict[str, Any]:
    descriptor = context.get("descriptor")
    metadata = getattr(descriptor, "metadata", None)
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def _derive_capability_id(context: dict[str, Any], resource: str | None = None) -> str | None:
    for key in ("capability_id", "resource", "tool_name"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(resource, str) and resource.strip():
        return resource.strip()
    descriptor = context.get("descriptor")
    value = getattr(descriptor, "id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _derive_risk_level(context: dict[str, Any], metadata: dict[str, Any]) -> RiskLevel | None:
    candidates: Iterable[Any] = (
        metadata.get("risk_level"),
        context.get("risk_level"),
        context.get("envelope_risk_level"),
    )
    for candidate in candidates:
        parsed = _coerce_risk_level(candidate)
        if parsed is not None:
            return parsed
    return None


def _derive_requires_approval(context: dict[str, Any], metadata: dict[str, Any]) -> bool:
    value = metadata.get("requires_approval", context.get("requires_approval", False))
    return bool(value)


async def _execute_callable(fn: Callable[[], Any]) -> Any:
    result = fn()
    if inspect.isawaitable(result):
        return await result
    return result


class NoOpSecurityBoundary(ISecurityBoundary):
    """Permissive boundary used for migration and local development."""

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        metadata = _descriptor_metadata(context)
        capability_id = _derive_capability_id(context)
        if capability_id is not None:
            metadata.setdefault("capability_id", capability_id)
        metadata["requires_approval"] = _derive_requires_approval(context, metadata)
        risk_level = _derive_risk_level(context, metadata) or RiskLevel.READ_ONLY
        return TrustedInput(params=dict(input), risk_level=risk_level, metadata=metadata)

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        _ = (action, resource, context)
        return PolicyDecision.ALLOW

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        _ = (action, sandbox)
        return await _execute_callable(fn)


class PolicySecurityBoundary(ISecurityBoundary):
    """Default policy boundary with deterministic decision mapping."""

    def __init__(
        self,
        *,
        deny_capability_ids: set[str] | None = None,
        approval_required_risk_levels: set[RiskLevel] | None = None,
        deny_risk_levels: set[RiskLevel] | None = None,
        default_decision: PolicyDecision = PolicyDecision.ALLOW,
        require_trusted_metadata: bool = False,
    ) -> None:
        self._deny_capability_ids = set(deny_capability_ids or set())
        self._approval_required_risk_levels = (
            set(approval_required_risk_levels)
            if approval_required_risk_levels is not None
            else {RiskLevel.NON_IDEMPOTENT_EFFECT}
        )
        self._deny_risk_levels = set(deny_risk_levels or set())
        self._default_decision = default_decision
        self._require_trusted_metadata = require_trusted_metadata

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> PolicySecurityBoundary:
        settings = dict(config or {})
        deny_capability_ids = _coerce_str_set(
            settings.get("deny_capability_ids", settings.get("blocked_capability_ids", []))
        )
        approval_required_risk_levels = _coerce_risk_levels(
            settings.get("approval_required_risk_levels"),
            default={RiskLevel.NON_IDEMPOTENT_EFFECT},
        )
        deny_risk_levels = _coerce_risk_levels(
            settings.get("deny_risk_levels"),
            default=set(),
        )
        default_decision = _coerce_policy_decision(
            settings.get("default_decision"),
            default=PolicyDecision.ALLOW,
        )
        require_trusted_metadata = bool(settings.get("require_trusted_metadata", False))
        return cls(
            deny_capability_ids=deny_capability_ids,
            approval_required_risk_levels=approval_required_risk_levels,
            deny_risk_levels=deny_risk_levels,
            default_decision=default_decision,
            require_trusted_metadata=require_trusted_metadata,
        )

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        metadata = _descriptor_metadata(context)
        capability_id = _derive_capability_id(context)
        if capability_id is None:
            raise SecurityBoundaryError(
                code=SECURITY_TRUST_DERIVATION_FAILED,
                message="missing trusted capability identifier",
                reason="capability_id not found in trusted context",
            )
        metadata["capability_id"] = capability_id

        risk_level = _derive_risk_level(context, metadata)
        if risk_level is None:
            if self._require_trusted_metadata:
                raise SecurityBoundaryError(
                    code=SECURITY_TRUST_DERIVATION_FAILED,
                    message=f"missing trusted risk metadata for capability '{capability_id}'",
                    reason="risk_level not derivable from trusted metadata",
                )
            risk_level = RiskLevel.READ_ONLY
            metadata.setdefault("risk_level", risk_level.value)
        else:
            metadata["risk_level"] = risk_level.value

        metadata["requires_approval"] = _derive_requires_approval(context, metadata)
        return TrustedInput(params=dict(input), risk_level=risk_level, metadata=metadata)

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        _ = action
        trusted = context.get("trusted_input")
        metadata = dict(getattr(trusted, "metadata", {})) if trusted is not None else _descriptor_metadata(context)
        capability_id = _derive_capability_id(context, resource) or resource
        risk_level = (
            getattr(trusted, "risk_level", None)
            if trusted is not None
            else _derive_risk_level(context, metadata)
        )
        if risk_level is None:
            risk_level = RiskLevel.READ_ONLY

        if capability_id in self._deny_capability_ids:
            return PolicyDecision.DENY
        if risk_level in self._deny_risk_levels:
            return PolicyDecision.DENY
        if _derive_requires_approval(context, metadata):
            return PolicyDecision.APPROVE_REQUIRED
        if risk_level in self._approval_required_risk_levels:
            return PolicyDecision.APPROVE_REQUIRED
        return self._default_decision

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        _ = (action, sandbox)
        return await _execute_callable(fn)


# Backward-compatible alias for legacy impl references.
DefaultSecurityBoundary = PolicySecurityBoundary


__all__ = [
    "DefaultSecurityBoundary",
    "NoOpSecurityBoundary",
    "PolicySecurityBoundary",
]
