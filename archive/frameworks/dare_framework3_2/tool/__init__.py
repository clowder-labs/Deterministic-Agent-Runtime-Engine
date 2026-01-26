"""Tool domain: tool execution and execution control.

This domain handles tool invocation, capability management,
protocol adapters, and execution control (pause/resume/checkpoint).
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.tool.component import (
    ITool,
    ISkill,
    ICapabilityProvider,
    IToolGateway,
    IProtocolAdapter,
    IMCPClient,
    IExecutionControl,
)

# Common types
from dare_framework3_2.tool.types import (
    ToolResult,
    ToolDefinition,
    CapabilityDescriptor,
    RiskLevel,
    ToolType,
    ExecutionSignal,
    Checkpoint,
    PauseRequested,
    CancelRequested,
    HumanApprovalRequired,
)

# Default implementations
from dare_framework3_2.tool.impl.default_tool_gateway import DefaultToolGateway
from dare_framework3_2.tool.impl.noop_tool import NoOpTool
from dare_framework3_2.tool.impl.run_command_tool import RunCommandTool
from dare_framework3_2.tool.impl.file_execution_control import FileExecutionControl

__all__ = [
    # Protocol
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IToolGateway",
    "IProtocolAdapter",
    "IMCPClient",
    "IExecutionControl",
    # Types
    "ToolResult",
    "ToolDefinition",
    "CapabilityDescriptor",
    "RiskLevel",
    "ToolType",
    "ExecutionSignal",
    "Checkpoint",
    "PauseRequested",
    "CancelRequested",
    "HumanApprovalRequired",
    # Implementations
    "DefaultToolGateway",
    "NoOpTool",
    "RunCommandTool",
    "FileExecutionControl",
]
