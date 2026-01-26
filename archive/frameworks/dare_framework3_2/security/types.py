"""Security domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    """Risk level classification for capabilities that may have side effects.
    
    Values:
        READ_ONLY: No side effects, safe to execute
        IDEMPOTENT_WRITE: Safe to retry without additional effects
        COMPENSATABLE: Has side effects but can be rolled back
        NON_IDEMPOTENT_EFFECT: Has permanent side effects, requires approval
    """
    READ_ONLY = "read_only"
    IDEMPOTENT_WRITE = "idempotent_write"
    COMPENSATABLE = "compensatable"
    NON_IDEMPOTENT_EFFECT = "non_idempotent_effect"


class PolicyDecision(Enum):
    """Policy decision returned by ISecurityBoundary.check_policy.
    
    Values:
        ALLOW: Action is permitted
        DENY: Action is denied
        APPROVE_REQUIRED: Action requires human approval
    """
    ALLOW = "allow"
    DENY = "deny"
    APPROVE_REQUIRED = "approve_required"


@dataclass(frozen=True)
class TrustedInput:
    """Trusted input derived from untrusted params + registries.
    
    Attributes:
        params: Validated parameters
        risk_level: Trusted risk level from registry
        metadata: Additional security metadata
    """
    params: dict[str, Any]
    risk_level: RiskLevel
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SandboxSpec:
    """Minimal sandbox specification placeholder.
    
    The MVP may stub sandbox behavior, but keeps the contract surface.
    
    Attributes:
        mode: Sandbox mode (e.g., "stub", "docker", "seccomp")
        details: Mode-specific configuration
    """
    mode: str = "stub"
    details: dict[str, Any] = field(default_factory=dict)
