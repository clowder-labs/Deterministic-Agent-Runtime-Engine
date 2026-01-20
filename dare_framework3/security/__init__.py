"""Security domain: Trust, Policy, and Sandbox boundary.

This domain provides the security infrastructure for the DARE Framework:
- ISecurityBoundary: Trust verification, policy checking, and sandbox execution

The security boundary is a Layer 0 Kernel interface that handles:
- Trust verification (deriving trusted fields from registries)
- Policy checking (allow/deny/require-approval decisions)
- Safe execution (sandbox isolation)

Factory Functions:
    create_default_security_boundary: Create default ISecurityBoundary
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3.security.interfaces import ISecurityBoundary

if TYPE_CHECKING:
    pass

__all__ = [
    # Interfaces
    "ISecurityBoundary",
    # Factory functions
    "create_default_security_boundary",
]


# =============================================================================
# Factory Functions
# =============================================================================

def create_default_security_boundary() -> ISecurityBoundary:
    """Create the default ISecurityBoundary implementation.
    
    Returns:
        A DefaultSecurityBoundary instance (permissive MVP implementation)
    """
    from dare_framework3.security.impl.default_security_boundary import DefaultSecurityBoundary
    return DefaultSecurityBoundary()
