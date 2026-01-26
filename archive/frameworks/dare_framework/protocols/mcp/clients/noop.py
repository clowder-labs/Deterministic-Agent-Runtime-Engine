from __future__ import annotations

from typing import Any

from dare_framework.builder.base_component import ConfigurableComponent
from dare_framework.contracts import ComponentType
from dare_framework.contracts.mcp import IMCPClient
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolDefinition, ToolResult


class NoOpMCPClient(ConfigurableComponent, IMCPClient):
    """A no-op MCP client used as a safe placeholder in early v2 milestones."""

    component_type = ComponentType.MCP
    name = "noop"

    @property
    def transport(self) -> str:
        return "noop"

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def list_tools(self) -> list[ToolDefinition]:
        return []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any], context: RunContext) -> ToolResult:
        return ToolResult(success=False, output={}, error="noop mcp client", evidence=[])

