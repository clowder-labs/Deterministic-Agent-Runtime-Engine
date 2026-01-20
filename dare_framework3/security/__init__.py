"""Security domain: trust, policy, and sandbox boundaries."""

from dare_framework3.security.component import ISecurityBoundary
from dare_framework3.security.types import RiskLevel, PolicyDecision, TrustedInput, SandboxSpec
from dare_framework3.security.impl.default_security_boundary import DefaultSecurityBoundary

__all__ = [
    "ISecurityBoundary",
    "RiskLevel",
    "PolicyDecision",
    "TrustedInput",
    "SandboxSpec",
    "DefaultSecurityBoundary",
]
