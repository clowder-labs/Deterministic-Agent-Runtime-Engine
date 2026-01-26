"""tool domain facade."""

from dare_framework3_4.tool.interfaces import (
    ICapabilityProvider,
    IProtocolAdapter,
    IMCPClient,
    ISkill,
    ITool,
    IToolProvider,
)
from dare_framework3_4.tool.kernel import IExecutionControl, IToolGateway
from dare_framework3_4.tool.types import (
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
from dare_framework3_4.tool._internal import (
    Checkpoint,
    DefaultExecutionControl,
    DefaultToolGateway,
    EchoTool,
    NativeToolProvider,
    NoopTool,
    ProtocolAdapterProvider,
)

# Built-in v4 tool runtime helpers and file tools
from dare_framework3_4.tool.internal import (
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

# Compatibility alias for examples
NoOpTool = NoopTool

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
    "IToolProvider",
    # Default implementations
    "Checkpoint",
    "DefaultExecutionControl",
    "DefaultToolGateway",
    "EchoTool",
    "NativeToolProvider",
    "NoopTool",
    "NoOpTool",
    "ProtocolAdapterProvider",
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
