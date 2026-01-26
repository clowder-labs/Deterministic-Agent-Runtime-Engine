"""MCP protocol client interfaces."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework2.tool.types import RunContext, ToolDefinition, ToolResult


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
        """List available tools."""
        ...

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Call a tool on the MCP server."""
        ...
