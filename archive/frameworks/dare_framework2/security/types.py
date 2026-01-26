"""Security domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dare_framework2.tool.types import RiskLevel


class PolicyDecision(Enum):
    """Policy decision returned by ISecurityBoundary.check_policy."""

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
    """Minimal sandbox specification placeholder."""

    mode: str = "stub"
    details: dict[str, Any] = field(default_factory=dict)
