"""Security domain component interfaces."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework.security.types import PolicyDecision, SandboxSpec, TrustedInput


class ITrustVerifier(Protocol):
    """Derive trusted fields from untrusted inputs and registries."""

    async def derive_trusted_input(
        self,
        *,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> TrustedInput:
        ...


class IPolicyEngine(Protocol):
    """Evaluate security policy for a proposed action."""

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        ...


class ISandbox(Protocol):
    """Sandbox execution boundary for risky operations."""

    async def execute(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        ...


__all__ = ["ITrustVerifier", "IPolicyEngine", "ISandbox"]
