"""Tool domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework3_4.security.types import RiskLevel
from dare_framework3_4.tool.types import CapabilityDescriptor, RunContext, ToolResult, ToolType, ToolDefinition


@runtime_checkable
class IToolProvider(Protocol):
    """[Component] Tool provider interface.

    Usage: Injected into Context to provide tool listings for prompt assembly.
    Tool definitions MUST be derived from the trusted capability registry.
    """

    def list_tools(self) -> list[dict[str, Any]]:
        """Get available tool definitions in LLM-compatible format."""
        ...


@runtime_checkable
class ITool(Protocol):
    """[Component] Executable tool contract."""

    @property
    def name(self) -> str:
        """[Component] Unique tool identifier."""
        ...

    @property
    def description(self) -> str:
        """[Component] Human-readable description."""
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        """[Component] JSON schema for input validation."""
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        """[Component] JSON schema for output validation."""
        ...

    @property
    def tool_type(self) -> ToolType:
        """[Component] Tool classification (atomic or work unit)."""
        ...

    @property
    def risk_level(self) -> RiskLevel:
        """[Component] Security risk classification for the tool."""
        ...

    @property
    def requires_approval(self) -> bool:
        """[Component] Whether human approval is required."""
        ...

    @property
    def timeout_seconds(self) -> int:
        """[Component] Execution timeout in seconds."""
        ...

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        """[Component] Assertions this tool can emit."""
        ...

    @property
    def is_work_unit(self) -> bool:
        """[Component] Whether this tool is a work unit."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """[Component] Execute the tool and return a ToolResult."""
        ...


@runtime_checkable
class ISkill(Protocol):
    """[Component] Pluggable skill capability."""

    @property
    def name(self) -> str:
        """[Component] Unique skill identifier."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """[Component] Execute the skill and return a ToolResult."""
        ...


class ICapabilityProvider(Protocol):
    """[Component] Provides capabilities to the tool gateway."""

    async def list(self) -> list[CapabilityDescriptor]:
        """[Component] List available capabilities."""
        ...

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        """[Component] Invoke a capability by id."""
        ...


@runtime_checkable
class IProtocolAdapter(Protocol):
    """[Component] Protocol adapter contract (Layer 1)."""

    @property
    def protocol_name(self) -> str:
        """[Component] Protocol name identifier."""
        ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        """[Component] Connect to an external protocol endpoint."""
        ...

    async def disconnect(self) -> None:
        """[Component] Disconnect from the protocol endpoint."""
        ...

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        """[Component] Discover remote capabilities."""
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any:
        """[Component] Invoke a remote capability."""
        ...


@runtime_checkable
class IMCPClient(Protocol):
    """[Component] Minimal MCP client interface for remote tools."""

    @property
    def name(self) -> str:
        """[Component] Client name identifier."""
        ...

    @property
    def transport(self) -> str:
        """[Component] Transport type (stdio, sse, etc.)."""
        ...

    async def connect(self) -> None:
        """[Component] Connect to the MCP server."""
        ...

    async def disconnect(self) -> None:
        """[Component] Disconnect from the MCP server."""
        ...

    async def list_tools(self) -> list[ToolDefinition]:
        """[Component] List available tools from the MCP server."""
        ...

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """[Component] Invoke a remote tool through MCP."""
        ...


__all__ = [
    "IToolProvider",
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IProtocolAdapter",
    "IMCPClient",
]
