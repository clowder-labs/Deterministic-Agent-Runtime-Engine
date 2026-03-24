"""tool domain facade."""

from __future__ import annotations

from dare_framework.tool.interfaces import IExecutionControl
from dare_framework.tool.kernel import ITool, IToolGateway, IToolManager, IToolProvider
from dare_framework.tool._exports import __getattr__
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    Evidence,
    ExecutionSignal,
    InvocationContext,
    ProviderStatus,
    RiskLevelName,
    RunContext,
    ToolDefinition,
    ToolErrorRecord,
    ToolResult,
    ToolSchema,
    ToolType,
)

__all__ = [
    # Types
    "CapabilityDescriptor",
    "CapabilityKind",
    "CapabilityMetadata",
    "CapabilityType",
    "Evidence",
    "ExecutionSignal",
    "InvocationContext",
    "ProviderStatus",
    "RiskLevelName",
    "RunContext",
    "ToolDefinition",
    "ToolErrorRecord",
    "ToolResult",
    "ToolSchema",
    "ToolType",
    # Kernel interfaces
    "IToolGateway",
    "IToolManager",
    # Pluggable interfaces
    "IExecutionControl",
    "ITool",
    "IToolProvider",
    # Supported defaults
    "ToolManager",
    # Built-in ask_user
    "AskUserTool",
    "AutoUserInputHandler",
    "CLIUserInputHandler",
    "IUserInputHandler",
]
