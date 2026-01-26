"""Tool domain: how to execute operations.

This domain handles capability definitions and executions,
including tools, skills, and capability providers.
"""

from dare_framework2.tool.components import ITool, ISkill, ICapabilityProvider
from dare_framework2.tool.kernel import IToolGateway
from dare_framework2.tool.types import (
    # Enums
    RiskLevel,
    ToolType,
    CapabilityType,
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
)

__all__ = [
    # Interfaces
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IToolGateway",
    # Enums
    "RiskLevel",
    "ToolType",
    "CapabilityType",
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
]
