"""Tool domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework3_3.security.types import RiskLevel
from dare_framework3_3.tool.types import (
    ToolResult,
    ToolType,
    CapabilityDescriptor,
    RunContext,
    ToolDefinition,
)

@runtime_checkable
class ITool(Protocol):
    """[Component] Executable tool contract.

    Usage: Implemented by capability providers for tool execution.
    """

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
        """[Component] Execute the tool and return a ToolResult.

        Usage: Called by providers or tool gateways to run the tool.
        """
        ...


@runtime_checkable
class ISkill(Protocol):
    """[Component] Pluggable skill capability.

    Usage: Used for higher-level operations or macros.
    """

    @property
    def name(self) -> str:
        """[Component] Unique skill identifier."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """[Component] Execute the skill and return a ToolResult.

        Usage: Invoked by planners or higher-level strategies.
        """
        ...


class ICapabilityProvider(Protocol):
    """[Component] Provides capabilities to the tool gateway.

    Usage: Implemented by local or remote capability providers.
    """

    async def list(self) -> list[CapabilityDescriptor]:
        """[Component] List available capabilities.

        Usage: Called by the tool gateway to build catalogs.
        """
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
    ) -> object:
        """[Component] Invoke a capability by id.

        Usage: Called by the tool gateway during execution.
        """
        ...


@runtime_checkable
class IProtocolAdapter(Protocol):
    """[Component] Protocol adapter contract (Layer 1).

    Usage: Bridges external protocols into the capability model.
    """

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
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IProtocolAdapter",
    "IMCPClient",
]
