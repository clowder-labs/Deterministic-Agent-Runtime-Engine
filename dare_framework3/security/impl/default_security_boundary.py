"""Default security boundary implementation."""

from __future__ import annotations

from typing import Any, Callable

from dare_framework3.security.interfaces import ISecurityBoundary
from dare_framework3.tool.types import (
    PolicyDecision,
    RiskLevel,
    SandboxSpec,
    TrustedInput,
)


class DefaultSecurityBoundary(ISecurityBoundary):
    """Composable security boundary with an MVP fail-closed policy.
    
    MVP policy rules:
    - READ_ONLY actions are allowed by default
    - Anything above READ_ONLY requires explicit approval
    - If a capability declares requires_approval, it always requires approval
    """

    async def verify_trust(
        self,
        *,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> TrustedInput:
        """Derive trusted input from context.
        
        The MVP keeps inputs unchanged but derives risk_level
        from trusted context where available.
        """
        risk_level = context.get("risk_level")
        if isinstance(risk_level, RiskLevel):
            derived_risk = risk_level
        else:
            derived_risk = RiskLevel.READ_ONLY
        
        return TrustedInput(
            params=dict(input),
            risk_level=derived_risk,
            metadata={},
        )

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Check policy for an action.
        
        Returns APPROVE_REQUIRED for anything above READ_ONLY.
        """
        risk_level = context.get("risk_level")
        requires_approval = bool(context.get("requires_approval", False))
        
        if requires_approval:
            return PolicyDecision.APPROVE_REQUIRED
        
        if isinstance(risk_level, RiskLevel) and risk_level != RiskLevel.READ_ONLY:
            return PolicyDecision.APPROVE_REQUIRED
        
        return PolicyDecision.ALLOW

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        """Execute a function.
        
        MVP: Sandbox is a stub. Policy MUST be enforced before calling.
        """
        result = fn()
        if hasattr(result, "__await__"):
            return await result
        return result
