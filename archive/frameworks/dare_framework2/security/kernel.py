"""Security domain kernel interfaces."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework2.security.types import PolicyDecision, SandboxSpec, TrustedInput


class ISecurityBoundary(Protocol):
    """Trust + Policy + Sandbox boundary."""

    async def verify_trust(
        self,
        *,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> TrustedInput:
        """Derive trusted input from untrusted parameters."""
        ...

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Check policy for an action."""
        ...

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        """Execute a function in a sandbox."""
        ...
