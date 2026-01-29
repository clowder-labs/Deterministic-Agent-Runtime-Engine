"""tool domain facade."""

from dare_framework.tool.interfaces import IMCPClient, ISkill, ITool, IToolProvider
from dare_framework.tool.kernel import IExecutionControl, IToolGateway, IToolManager
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    Evidence,
    ExecutionSignal,
    PauseRequested,
    CancelRequested,
    HumanApprovalRequired,
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

# Default/internal implementations
from dare_framework.tool._internal import (
    Checkpoint,
    DefaultExecutionControl,
    EchoTool,
    MCPToolkit,
    NativeToolProvider,
    NoopTool,
    ToolManager,
)
from dare_framework.tool._internal import NoopTool as NoOpTool

# Built-in v4 tool runtime helpers and file tools
from dare_framework.tool._internal import (
    EditLineTool,
    FileExecutionControl,
    NoOpMCPClient,
    NoOpSkill,
    ReadFileTool,
    RunCommandTool,
    RunContextState,
    SearchCodeTool,
    WriteFileTool,
)

__all__ = [
    # Types
    "CapabilityDescriptor",
    "CapabilityKind",
    "CapabilityMetadata",
    "CapabilityType",
    "Evidence",
    "ExecutionSignal",
    "PauseRequested",
    "CancelRequested",
    "HumanApprovalRequired",
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
    "IExecutionControl",
    "IToolGateway",
    "IToolManager",
    # Pluggable interfaces
    "IMCPClient",
    "ISkill",
    "ITool",
    "IToolProvider",
    # Default implementations
    "Checkpoint",
    "DefaultExecutionControl",
    "EchoTool",
    "MCPToolkit",
    "NativeToolProvider",
    "NoopTool",
    "NoOpTool",
    "ToolManager",
    # v4 tool runtime helpers and file tools
    "NoOpMCPClient",
    "NoOpSkill",
    "RunCommandTool",
    "RunContextState",
    "FileExecutionControl",
    "ReadFileTool",
    "SearchCodeTool",
    "WriteFileTool",
    "EditLineTool",
]
