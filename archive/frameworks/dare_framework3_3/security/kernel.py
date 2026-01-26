"""Security domain kernel interfaces."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework3_3.security.types import PolicyDecision, SandboxSpec, TrustedInput


class ISecurityBoundary(Protocol):
    """[Kernel] Trust + policy + sandbox enforcement boundary.

    Usage: Called by the agent before invoking tools or external actions.
    """

    async def verify_trust(
        self,
        *,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> TrustedInput:
        """[Kernel] Derive trusted input from untrusted parameters.

        Usage: Called before policy checks to normalize risk metadata.
        """
        ...

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """[Kernel] Evaluate policy decision for an action.

        Usage: Called before execution to enforce allow/deny rules.
        """
        ...

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        """[Kernel] Execute an action within a sandbox boundary.

        Usage: Called after policy approval to run the action safely.
        """
        ...


__all__ = ["ISecurityBoundary"]
