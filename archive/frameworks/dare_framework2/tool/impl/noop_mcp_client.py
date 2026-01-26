"""No-op MCP client implementation."""

from __future__ import annotations

from typing import Any

from dare_framework2.protocols.mcp.interfaces import IMCPClient
from dare_framework2.tool.types import RunContext, ToolDefinition, ToolResult


class NoOpMCPClient(IMCPClient):
    """A no-op MCP client used as a safe placeholder.
    
    Returns empty tool lists and fails all tool calls.
    """

    @property
    def name(self) -> str:
        return "noop"

    @property
    def transport(self) -> str:
        return "noop"

    async def connect(self) -> None:
        """No-op connection."""
        pass

    async def disconnect(self) -> None:
        """No-op disconnection."""
        pass

    async def list_tools(self) -> list[ToolDefinition]:
        """Returns empty tool list."""
        return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Always fails - this is a no-op client."""
        return ToolResult(
            success=False,
            output={},
            error="noop mcp client",
            evidence=[],
        )
