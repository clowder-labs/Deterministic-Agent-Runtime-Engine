"""security domain stable interfaces.

Alignment notes:
- `verify_trust` derives security-critical fields from trusted registries.
- `check_policy` returns ALLOW/DENY/APPROVE_REQUIRED decisions.
- `execute_safe` represents a sandboxed execution wrapper.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework.security.types import PolicyDecision, SandboxSpec, TrustedInput


class ISecurityBoundary(Protocol):
    """Trust + policy + sandbox boundary."""

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        """Derive trusted input from untrusted parameters."""

        ...

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Evaluate policy decision for an action."""

        ...

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        """Execute an action within a sandbox boundary."""

        ...


__all__ = ["ISecurityBoundary"]
