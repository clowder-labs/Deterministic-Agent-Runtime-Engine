"""Tool domain component interfaces (Protocol definitions)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence, runtime_checkable

from dare_framework3_2.tool.types import (
    ToolResult,
    ToolType,
    RiskLevel,
    CapabilityDescriptor,
    RunContext,
    ToolDefinition,
    ExecutionSignal,
)

if TYPE_CHECKING:
    from dare_framework3_2.plan.types import Envelope


# =============================================================================
# Tool Interface (Layer 2 Component)
# =============================================================================

@runtime_checkable
class ITool(Protocol):
    """Executable tool contract.
    
    Tools are capability implementations. Side effects must be routed
    through the Kernel IToolGateway boundary, but tool implementations
    are kept as plain Python objects for ease of extension.
    """

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for input validation."""
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        """JSON Schema for output."""
        ...

    @property
    def tool_type(self) -> ToolType:
        """Tool classification (atomic or work unit)."""
        ...

    @property
    def risk_level(self) -> RiskLevel:
        """Security risk classification."""
        ...

    @property
    def requires_approval(self) -> bool:
        """Whether HITL approval is required."""
        ...

    @property
    def timeout_seconds(self) -> int:
        """Execution timeout in seconds."""
        ...

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        """Assertions this tool can produce."""
        ...

    @property
    def is_work_unit(self) -> bool:
        """Whether this is a work unit tool."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Execute the tool.
        
        Args:
            input: Tool input parameters
            context: Execution context
            
        Returns:
            Tool execution result with evidence
        """
        ...


# =============================================================================
# Skill Interface (Layer 2 Component)
# =============================================================================

@runtime_checkable
class ISkill(Protocol):
    """A pluggable skill capability.
    
    Skills are similar to tools but may be used for higher-level
    operations or plan-time macros.
    """

    @property
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Execute the skill.
        
        Args:
            input: Skill input parameters
            context: Execution context
            
        Returns:
            Execution result
        """
        ...


# =============================================================================
# Capability Provider Interface (Layer 2 Component)
# =============================================================================

class ICapabilityProvider(Protocol):
    """Provides capabilities to the Kernel tool gateway.
    
    Capability providers abstract the source of capabilities,
    whether they are local tools, MCP servers, or other agents.
    """

    async def list(self) -> list[CapabilityDescriptor]:
        """List all available capabilities.
        
        Returns:
            List of capability descriptors
        """
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
    ) -> object:
        """Invoke a capability.
        
        Args:
            capability_id: The capability to invoke
            params: Invocation parameters
            
        Returns:
            Capability result
        """
        ...


# =============================================================================
# Tool Gateway Interface (Layer 0 Kernel)
# =============================================================================

class IToolGateway(Protocol):
    """System call boundary and unified invocation entry.
    
    The tool gateway is the single point of entry for all capability
    invocations, enforcing security policies and routing to providers.
    """

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        """List all available capabilities from all providers.
        
        Returns:
            Sequence of capability descriptors
        """
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        """Invoke a capability within an execution envelope.
        
        Args:
            capability_id: The capability to invoke
            params: Invocation parameters
            envelope: Execution boundary constraints
            
        Returns:
            Capability result
        """
        ...

    def register_provider(self, provider: ICapabilityProvider) -> None:
        """Register a capability provider.
        
        Args:
            provider: The provider to register
        """
        ...


# =============================================================================
# Protocol Adapter Interface (Layer 1)
# =============================================================================

@runtime_checkable
class IProtocolAdapter(Protocol):
    """Protocol adapter contract (Layer 1).
    
    Protocol adapters translate external protocols (MCP, A2A, etc.)
    into the framework's canonical capability model.
    """

    @property
    def protocol_name(self) -> str:
        """The name of the protocol (e.g., 'mcp', 'a2a')."""
        ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        """Connect to the protocol endpoint.
        
        Args:
            endpoint: Connection endpoint
            config: Connection configuration
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from the protocol endpoint."""
        ...

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        """Discover remote capabilities.
        
        Returns:
            Sequence of discovered capability descriptors
        """
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any:
        """Invoke a remote capability.
        
        Args:
            capability_id: The capability to invoke
            params: Invocation parameters
            timeout: Optional timeout in seconds
            
        Returns:
            Capability result
        """
        ...


# =============================================================================
# MCP Client Interface (Layer 1)
# =============================================================================

@runtime_checkable
class IMCPClient(Protocol):
    """Minimal MCP client interface for discovering and invoking remote tools."""

    @property
    def name(self) -> str:
        """Client name identifier."""
        ...

    @property
    def transport(self) -> str:
        """Transport type (e.g., 'stdio', 'sse')."""
        ...

    async def connect(self) -> None:
        """Connect to the MCP server."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        ...

    async def list_tools(self) -> list[ToolDefinition]:
        """List available tools.
        
        Returns:
            List of tool definitions
        """
        ...

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            context: Execution context
            
        Returns:
            Tool result
        """
        ...


# =============================================================================
# Execution Control Interface (migrated from runtime/ in v3.2)
# =============================================================================

class IExecutionControl(Protocol):
    """Pause/resume/checkpoint control plane.
    
    Enables external control over execution, including pausing,
    resuming, checkpointing, and human-in-the-loop integration.
    
    Migrated from runtime/ in v3.2 as it primarily controls tool execution.
    """

    def poll(self) -> ExecutionSignal:
        """Poll for control signals.
        
        Returns:
            Current execution signal (NONE if no signal)
        """
        ...

    def poll_or_raise(self) -> None:
        """Raise a standardized exception for non-NONE signals.
        
        Raises:
            PauseRequested: If pause was requested
            CancelRequested: If cancellation was requested
            HumanApprovalRequired: If human approval is required
        """
        ...

    async def pause(self, reason: str) -> str:
        """Enter PAUSED state and create a checkpoint.
        
        Args:
            reason: Human-readable pause reason
            
        Returns:
            Checkpoint ID
        """
        ...

    async def resume(self, checkpoint_id: str) -> None:
        """Resume from a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to resume from
        """
        ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        """Create an explicit checkpoint with attached payload.
        
        Args:
            label: Checkpoint label
            payload: Checkpoint data
            
        Returns:
            Checkpoint ID
        """
        ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        """Request/record a HITL waiting point.
        
        Args:
            checkpoint_id: Associated checkpoint ID
            reason: Reason for human approval
        """
        ...
