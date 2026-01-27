"""tool domain facade."""

from dare_framework.tool.interfaces import (
    ICapabilityProvider,
    IProtocolAdapter,
    IMCPClient,
    ISkill,
    ITool,
    IToolManager,
    IToolProvider,
)
from dare_framework.tool.kernel import IExecutionControl, IToolGateway
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
    DefaultToolGateway,
    EchoTool,
    MCPToolkit,
    NativeToolProvider,
    NoopTool,
    ProtocolAdapterProvider,
    ToolManager,
)
from dare_framework.tool._internal import NoopTool as NoOpTool

# Built-in v4 tool runtime helpers and file tools
from dare_framework.tool._internal import (
    EditLineTool,
    FileExecutionControl,
    GatewayToolProvider,
    MCPAdapter,
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
    # Pluggable interfaces
    "ICapabilityProvider",
    "IProtocolAdapter",
    "IMCPClient",
    "ISkill",
    "ITool",
    "IToolManager",
    "IToolProvider",
    # Default implementations
    "Checkpoint",
    "DefaultExecutionControl",
    "DefaultToolGateway",
    "EchoTool",
    "MCPToolkit",
    "NativeToolProvider",
    "NoopTool",
    "NoOpTool",
    "ProtocolAdapterProvider",
    "ToolManager",
    # v4 tool runtime helpers and file tools
    "GatewayToolProvider",
    "MCPAdapter",
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
