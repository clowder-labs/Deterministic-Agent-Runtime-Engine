"""MCP domain stable interfaces (Kernel boundaries)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import RunContext, ToolResult


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

    async def list_tools(self) -> list[ITool]:
        """List available tools from the MCP server as framework-native ITool objects."""
        ...

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Invoke a remote tool through MCP."""
        ...


__all__ = ["IMCPClient"]
