from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from dare_framework.contracts.risk import RiskLevel


class PolicyDecision(Enum):
    """Policy decision returned by ISecurityBoundary.check_policy (v2.0)."""

    ALLOW = "allow"
    DENY = "deny"
    APPROVE_REQUIRED = "approve_required"


@dataclass(frozen=True)
class TrustedInput:
    """Trusted input derived from untrusted params + registries."""

    params: dict[str, Any]
    risk_level: RiskLevel
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SandboxSpec:
    """Minimal sandbox specification placeholder (v2.0).

    The MVP may stub sandbox behavior, but MUST keep the contract surface.
    """

    mode: str = "stub"
    details: dict[str, Any] = field(default_factory=dict)


class ISecurityBoundary(Protocol):
    """Trust + Policy + Sandbox boundary (v2.0, composable)."""

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput: ...

    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision: ...

    async def execute_safe(self, *, action: str, fn: Callable[[], Any], sandbox: SandboxSpec) -> Any: ...
