"""Tool domain: how to execute operations.

This domain handles all capability definitions and executions,
including tools, skills, and protocol adapters.
"""

from dare_framework2.tool.interfaces import (
    ITool,
    ISkill,
    ICapabilityProvider,
    IToolGateway,
    IProtocolAdapter,
    ISecurityBoundary,
    IMCPClient,
)
from dare_framework2.tool.types import (
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

__all__ = [
    # Interfaces
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IToolGateway",
    "IProtocolAdapter",
    "ISecurityBoundary",
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
    # Security
    "TrustedInput",
    "SandboxSpec",
]
