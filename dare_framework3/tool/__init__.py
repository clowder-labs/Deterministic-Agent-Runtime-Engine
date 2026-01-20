"""Tool domain: how to execute operations.

This domain handles all capability definitions and executions,
including tools, skills, and protocol adapters.

Note: ISecurityBoundary has been moved to the security/ domain in v3.1.

Factory Functions:
    create_default_tool_gateway: Create default IToolGateway
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3.tool.interfaces import (
    ITool,
    ISkill,
    ICapabilityProvider,
    IToolGateway,
    IProtocolAdapter,
    IMCPClient,
)
from dare_framework3.tool.types import (
    # Enums
    RiskLevel,
    ToolType,
    CapabilityType,
    PolicyDecision,
    # Evidence
    Evidence,
    # Tool types
    ToolDefinition,
    ToolResult,
    ToolErrorRecord,
    # Capability
    CapabilityDescriptor,
    # Context
    RunContext,
    # Security
    TrustedInput,
    SandboxSpec,
)

if TYPE_CHECKING:
    pass

__all__ = [
    # Interfaces
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IToolGateway",
    "IProtocolAdapter",
    "IMCPClient",
    # Enums
    "RiskLevel",
    "ToolType",
    "CapabilityType",
    "PolicyDecision",
    # Evidence
    "Evidence",
    # Tool types
    "ToolDefinition",
    "ToolResult",
    "ToolErrorRecord",
    # Capability
    "CapabilityDescriptor",
    # Context
    "RunContext",
    # Security types (kept here for compatibility)
    "TrustedInput",
    "SandboxSpec",
    # Factory functions
    "create_default_tool_gateway",
]


# =============================================================================
# Factory Functions
# =============================================================================

def create_default_tool_gateway() -> IToolGateway:
    """Create the default IToolGateway implementation.
    
    Returns:
        A DefaultToolGateway instance (empty, ready for providers)
    """
    from dare_framework3.tool.impl.default_tool_gateway import DefaultToolGateway
    return DefaultToolGateway()
