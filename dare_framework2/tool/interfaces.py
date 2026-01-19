"""Tool domain interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Protocol, Sequence, runtime_checkable

from dare_framework2.tool.types import (
    ToolResult,
    ToolType,
    RiskLevel,
    CapabilityDescriptor,
    RunContext,
    TrustedInput,
    PolicyDecision,
    SandboxSpec,
    ToolDefinition,
)

if TYPE_CHECKING:
    from dare_framework2.plan.types import Envelope


# =============================================================================
# Tool Interface
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
# Skill Interface
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
# Capability Provider Interface
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
# Tool Gateway Interface
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
# Protocol Adapter Interface
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
# Security Boundary Interface
# =============================================================================

class ISecurityBoundary(Protocol):
    """Trust + Policy + Sandbox boundary.
    
    The security boundary handles:
    - Trust verification (deriving trusted fields from registries)
    - Policy checking (allow/deny/require-approval)
    - Safe execution (sandbox isolation)
    """

    async def verify_trust(
        self,
        *,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> TrustedInput:
        """Derive trusted input from untrusted parameters.
        
        Args:
            input: Untrusted input parameters
            context: Security context (registry info, etc.)
            
        Returns:
            Trusted input with derived security fields
        """
        ...

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Check policy for an action.
        
        Args:
            action: The action being performed
            resource: The resource being accessed
            context: Security context
            
        Returns:
            Policy decision (allow/deny/require-approval)
        """
        ...

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        """Execute a function in a sandbox.
        
        Args:
            action: Description of the action
            fn: The function to execute
            sandbox: Sandbox configuration
            
        Returns:
            Function result
        """
        ...


# =============================================================================
# MCP Client Interface
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
