"""Tool domain: capability definitions and execution control."""

from dare_framework3.tool.component import (
    ITool,
    ISkill,
    ICapabilityProvider,
    IToolGateway,
    IProtocolAdapter,
    IMCPClient,
    IExecutionControl,
)
from dare_framework3.tool.types import (
    ExecutionSignal,
    PauseRequested,
    CancelRequested,
    HumanApprovalRequired,
    Checkpoint,
    ToolType,
    CapabilityType,
    Evidence,
    ToolDefinition,
    ToolSchema,
    ToolResult,
    ToolErrorRecord,
    CapabilityDescriptor,
    RunContext,
)
from dare_framework3.tool.impl.default_tool_gateway import DefaultToolGateway
from dare_framework3.tool.impl.native_tool_provider import NativeToolProvider
from dare_framework3.tool.impl.protocol_adapter_provider import ProtocolAdapterProvider
from dare_framework3.tool.impl.noop_tool import NoOpTool
from dare_framework3.tool.impl.noop_skill import NoOpSkill
from dare_framework3.tool.impl.run_command_tool import RunCommandTool
from dare_framework3.tool.impl.mcp_adapter import MCPAdapter
from dare_framework3.tool.impl.noop_mcp_client import NoOpMCPClient
from dare_framework3.tool.impl.run_context_state import RunContextState
from dare_framework3.tool.impl.file_execution_control import FileExecutionControl

__all__ = [
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IToolGateway",
    "IProtocolAdapter",
    "IMCPClient",
    "IExecutionControl",
    "ExecutionSignal",
    "PauseRequested",
    "CancelRequested",
    "HumanApprovalRequired",
    "Checkpoint",
    "ToolType",
    "CapabilityType",
    "Evidence",
    "ToolDefinition",
    "ToolSchema",
    "ToolResult",
    "ToolErrorRecord",
    "CapabilityDescriptor",
    "RunContext",
    "DefaultToolGateway",
    "NativeToolProvider",
    "ProtocolAdapterProvider",
    "NoOpTool",
    "NoOpSkill",
    "RunCommandTool",
    "MCPAdapter",
    "NoOpMCPClient",
    "RunContextState",
    "FileExecutionControl",
]
