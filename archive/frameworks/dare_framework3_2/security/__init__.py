"""Security domain: trust, policy, and sandbox boundary.

This domain handles security-related operations including
trust verification, policy checking, and sandboxed execution.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.security.component import ISecurityBoundary

# Common types
from dare_framework3_2.security.types import (
    RiskLevel,
    PolicyDecision,
    TrustedInput,
    SandboxSpec,
)

# Default implementations
from dare_framework3_2.security.impl.default_security_boundary import DefaultSecurityBoundary

__all__ = [
    # Protocol
    "ISecurityBoundary",
    # Types
    "RiskLevel",
    "PolicyDecision",
    "TrustedInput",
    "SandboxSpec",
    # Implementations
    "DefaultSecurityBoundary",
]
