"""tool domain pluggable interfaces (implementations).

This module intentionally focuses on interface declarations only.
Concrete implementations (native tools, protocol adapters, gateways) live under
`_internal/` or other internal modules.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolDefinition,
    ToolResult,
    ToolType,
)


@runtime_checkable
class IToolProvider(Protocol):
    """[Component] Tool provider interface.

    Usage: Tool source for registration into ToolManager.
    Provides tool instances rather than tool definitions.

    Note: Tool execution boundaries and control-plane contracts are declared in
    `dare_framework.tool.kernel` (v4-style alignment).
    """

    def list_tools(self) -> list["ITool"]:
        """Get available tool instances for registration.

        Returns:
            List of tool implementations.
        """
        ...


@runtime_checkable
class ITool(IComponent, Protocol):
    """A callable tool implementation (V4 compliant).

    All metadata properties are trusted registry sources, not model output.
    """

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.TOOL]:
        """Component category used for config scoping."""
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
class ISkill(IComponent, Protocol):
    """Pluggable skill capability for higher-level operations."""

    @property
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.SKILL]:
        """Component category used for config scoping."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        """Execute the skill and return a ToolResult."""
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
    "ISkill",
    "ITool",
    "IToolProvider",
    "IMCPClient",
    "RunContext",
    "ToolDefinition",
    "ToolResult",
]
