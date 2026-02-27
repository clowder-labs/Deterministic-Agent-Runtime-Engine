"""security domain facade."""

from dare_framework.security.errors import (
    SECURITY_APPROVAL_MANAGER_MISSING,
    SECURITY_POLICY_CHECK_FAILED,
    SECURITY_POLICY_DENIED,
    SECURITY_TRUST_DERIVATION_FAILED,
    SecurityBoundaryError,
)
from dare_framework.security.impl import (
    DefaultSecurityBoundary,
    NoOpSecurityBoundary,
    PolicySecurityBoundary,
)
from dare_framework.security.kernel import ISecurityBoundary
from dare_framework.security.types import PolicyDecision, RiskLevel, SandboxSpec, TrustedInput

__all__ = [
    "DefaultSecurityBoundary",
    "ISecurityBoundary",
    "NoOpSecurityBoundary",
    "PolicyDecision",
    "PolicySecurityBoundary",
    "RiskLevel",
    "SECURITY_APPROVAL_MANAGER_MISSING",
    "SECURITY_POLICY_CHECK_FAILED",
    "SECURITY_POLICY_DENIED",
    "SECURITY_TRUST_DERIVATION_FAILED",
    "SandboxSpec",
    "SecurityBoundaryError",
    "TrustedInput",
]
