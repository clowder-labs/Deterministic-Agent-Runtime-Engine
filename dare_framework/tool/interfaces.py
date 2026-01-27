"""tool domain pluggable interfaces (implementations).

This module intentionally focuses on interface declarations only.
Concrete implementations (native tools, protocol adapters, gateways) live under
`_internal/` or other internal modules.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    ProviderStatus,
    RiskLevelName,
    RunContext,
    ToolDefinition,
    ToolResult,
    ToolType,
)


@runtime_checkable
class IToolProvider(Protocol):
    """[Component] Tool provider interface.

    Usage: Injected into BaseContext.tools.
    Provides tool listing capability for context assembly.

    Note: This is a minimal interface for BaseContext integration.
    Tool execution boundaries and control-plane contracts are declared in
    `dare_framework.tool.kernel` (v4-style alignment).
    """

    def list_tools(self) -> list[dict[str, Any]]:
        """Get available tool definitions in LLM-compatible format.

        Returns:
            List of tool definitions with name, description, parameters, etc.
        """
        ...


@runtime_checkable
class ITool(Protocol):
    """A callable tool implementation (V4 compliant).

    All metadata properties are trusted registry sources, not model output.
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
        """JSON schema for input validation."""
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        """JSON schema for output validation."""
        ...

    @property
    def tool_type(self) -> ToolType:
        """Tool classification (atomic or work unit)."""
        ...

    @property
    def risk_level(self) -> RiskLevelName:
        """Security risk classification (trusted registry source)."""
        ...

    @property
    def requires_approval(self) -> bool:
        """Whether human approval is required (trusted registry source)."""
        ...

    @property
    def timeout_seconds(self) -> int:
        """Execution timeout in seconds."""
        ...

    @property
    def is_work_unit(self) -> bool:
        """Whether this tool is a work unit (envelope-bounded loop)."""
        ...

    @property
    def capability_kind(self) -> CapabilityKind:
        """Capability kind for trusted registry metadata."""
        ...

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        """Execute the tool and return a ToolResult."""
        ...


@runtime_checkable
class IToolManager(Protocol):
    """Trusted tool registry and provider aggregation interface."""

    def register_tool(
        self,
        tool: ITool,
        *,
        namespace: str | None = None,
        version: str | None = None,
    ) -> CapabilityDescriptor:
        """Register a tool and return its capability descriptor."""
        ...

    def unregister_tool(self, capability_id: str) -> bool:
        """Unregister a tool capability by id."""
        ...

    def update_tool(
        self,
        tool: ITool,
        *,
        capability_id: str,
        enabled: bool | None = None,
    ) -> CapabilityDescriptor:
        """Update a registered tool capability."""
        ...

    def set_capability_enabled(self, capability_id: str, enabled: bool) -> None:
        """Enable or disable a capability in the registry."""
        ...

    def register_provider(self, provider: "ICapabilityProvider") -> None:
        """Register a capability provider."""
        ...

    def unregister_provider(self, provider: "ICapabilityProvider") -> bool:
        """Unregister a capability provider."""
        ...

    async def refresh(self) -> list[CapabilityDescriptor]:
        """Refresh provider capabilities into the registry."""
        ...

    def list_capabilities(self, *, include_disabled: bool = False) -> list[CapabilityDescriptor]:
        """List registered capabilities."""
        ...

    def list_tool_defs(self) -> list[ToolDefinition]:
        """List tool definitions derived from the registry."""
        ...

    def get_capability(
        self,
        capability_id: str,
        *,
        include_disabled: bool = False,
    ) -> CapabilityDescriptor | None:
        """Fetch a capability descriptor by id."""
        ...

    async def health_check(self) -> dict[str, ProviderStatus]:
        """Check provider health status."""
        ...


@runtime_checkable
class ISkill(Protocol):
    """Pluggable skill capability for higher-level operations."""

    @property
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        """Execute the skill and return a ToolResult."""
        ...


@runtime_checkable
class ICapabilityProvider(Protocol):
    """A provider that exposes capabilities to a ToolGateway registry."""

    async def list(self) -> list[CapabilityDescriptor]:
        """List available capabilities."""
        ...

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        """Invoke a capability by id."""
        ...

    async def health_check(self) -> ProviderStatus:
        """Check provider health status."""
        ...


@runtime_checkable
class IProtocolAdapter(Protocol):
    """Protocol adapter (e.g., MCP/A2A) translated into canonical capabilities."""

    @property
    def protocol_name(self) -> str:
        """Protocol name identifier."""
        ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        """Connect to an external protocol endpoint."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the protocol endpoint."""
        ...

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        """Discover remote capabilities."""
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any:
        """Invoke a remote capability."""
        ...


@runtime_checkable
class IMCPClient(Protocol):
    """Minimal MCP client interface for remote tools."""

    @property
    def name(self) -> str:
        """Client name identifier."""
        ...

    @property
    def transport(self) -> str:
        """Transport type (stdio, sse, etc.)."""
        ...

    async def connect(self) -> None:
        """Connect to the MCP server."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        ...

    async def list_tools(self) -> list[ToolDefinition]:
        """List available tools from the MCP server."""
        ...

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Invoke a remote tool through MCP."""
        ...


__all__ = [
    "ICapabilityProvider",
    "IProtocolAdapter",
    "ISkill",
    "IToolManager",
    "ITool",
    "IToolProvider",
    "IMCPClient",
    "RunContext",
    "ToolDefinition",
    "ToolResult",
]
