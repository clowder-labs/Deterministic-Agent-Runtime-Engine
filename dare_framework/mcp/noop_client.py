"""No-op MCP client implementation (internal use)."""

from __future__ import annotations

from typing import Any

from dare_framework.mcp.kernel import IMCPClient
from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import RunContext, ToolResult


class NoOpMCPClient(IMCPClient):
    """A no-op MCP client used as a safe placeholder."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def transport(self) -> str:
        return "noop"

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def list_tools(self) -> list[ITool]:
        return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        return ToolResult(
            success=False,
            output={},
            error="noop mcp client",
            evidence=[],
        )


__all__ = ["NoOpMCPClient"]
