"""Kernel security boundary protocols (v2)."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework.security.types import PolicyDecision, SandboxSpec, TrustedInput


class ISecurityBoundary(Protocol):
    """Trust + Policy + Sandbox boundary (v2.0, composable)."""

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput: ...

    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision: ...

    async def execute_safe(self, *, action: str, fn: Callable[[], Any], sandbox: SandboxSpec) -> Any: ...

