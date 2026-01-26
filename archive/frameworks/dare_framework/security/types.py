"""Kernel security boundary models (v2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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

