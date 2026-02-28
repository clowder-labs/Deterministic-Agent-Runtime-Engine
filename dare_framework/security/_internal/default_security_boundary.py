"""Default security boundary implementation for canonical runtime."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from dare_framework.security.kernel import ISecurityBoundary
from dare_framework.security.types import PolicyDecision, RiskLevel, SandboxSpec, TrustedInput


class DefaultSecurityBoundary(ISecurityBoundary):
    """Default permissive boundary.

    This implementation is intentionally minimal:
    - trust derivation normalizes params/risk fields
    - policy gate defaults to ALLOW
    - execute_safe wraps execution and awaits async callables
    """

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        params = dict(input or {})
        risk_level = self._coerce_risk_level(context.get("risk_level"))
        metadata = {
            "capability_id": context.get("capability_id"),
            "source": "default_security_boundary",
        }
        return TrustedInput(params=params, risk_level=risk_level, metadata=metadata)

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
        value = fn()
        if inspect.isawaitable(value):
            return await value
        return value

    def _coerce_risk_level(self, value: Any) -> RiskLevel:
        if isinstance(value, RiskLevel):
            return value
        if hasattr(value, "value"):
            value = value.value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for candidate in RiskLevel:
                if candidate.value == normalized:
                    return candidate
        return RiskLevel.READ_ONLY


__all__ = ["DefaultSecurityBoundary"]
