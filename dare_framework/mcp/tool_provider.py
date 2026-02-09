"""MCP tool provider integration."""

from __future__ import annotations

from typing import Any, Sequence

from dare_framework.mcp.kernel import IMCPClient
from dare_framework.tool.kernel import ITool, IToolProvider
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)


class MCPToolProvider(IToolProvider):
    """Expose MCP client tools as framework ITool instances."""

    def __init__(self, clients: Sequence[IMCPClient]) -> None:
        self._clients = list(clients)
        self._tools: dict[str, MCPTool] = {}

    async def initialize(self) -> None:
        """Connect clients and cache their tools."""
        self._tools.clear()
        for client in self._clients:
            await client.connect()
            for tool_def in await client.list_tools():
                tool_name = _tool_field(tool_def, "name", "")
                if not tool_name:
                    continue
                full_name = f"{client.name}:{tool_name}"
                self._tools[full_name] = MCPTool(
                    client=client,
                    tool_def=tool_def,
                    tool_name=tool_name,
                    full_name=full_name,
                )

    async def close(self) -> None:
        """Disconnect all MCP clients."""
        for client in self._clients:
            await client.disconnect()

    def list_tools(self) -> list[ITool]:
        """Return the cached MCP tools."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> ITool | None:
        """Return a cached tool by its full name."""
        return self._tools.get(name)


class MCPTool(ITool):
    """Adapter that wraps a single MCP tool definition."""

    def __init__(
        self,
        *,
        client: IMCPClient,
        tool_def: Any,
        tool_name: str,
        full_name: str,
    ) -> None:
        self._client = client
        self._tool_def = tool_def
        self._tool_name = tool_name
        self._full_name = full_name

    @property
    def name(self) -> str:
        return self._full_name

    @property
    def description(self) -> str:
        return str(_tool_field(self._tool_def, "description", ""))

    @property
    def input_schema(self) -> dict[str, Any]:
        # MCP servers commonly return camelCase `inputSchema`; keep snake_case for compatibility.
        value = _tool_field(self._tool_def, "input_schema", {}, aliases=("inputSchema",))
        return dict(value) if isinstance(value, dict) else {}

    @property
    def output_schema(self) -> dict[str, Any]:
        value = _tool_field(self._tool_def, "output_schema", {}, aliases=("outputSchema",))
        return dict(value) if isinstance(value, dict) else {}

    @property
    def tool_type(self) -> ToolType:
        return ToolType.WORK_UNIT if self.is_work_unit else ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        value = _tool_field(self._tool_def, "risk_level", "read_only")
        return _normalize_risk_level(value)

    @property
    def requires_approval(self) -> bool:
        return bool(_tool_field(self._tool_def, "requires_approval", False))

    @property
    def timeout_seconds(self) -> int:
        value = _tool_field(self._tool_def, "timeout_seconds", 30)
        return int(value) if isinstance(value, (int, float, str)) else 30

    @property
    def is_work_unit(self) -> bool:
        return bool(_tool_field(self._tool_def, "is_work_unit", False))

    @property
    def capability_kind(self) -> CapabilityKind:
        value = _tool_field(self._tool_def, "capability_kind", CapabilityKind.TOOL)
        return _normalize_capability_kind(value)

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        return await self._client.call_tool(self._tool_name, input, context=context)


def _tool_field(
    tool_def: Any,
    field: str,
    default: Any,
    *,
    aliases: tuple[str, ...] = (),
) -> Any:
    if isinstance(tool_def, dict):
        if field in tool_def:
            return tool_def[field]
        for alias in aliases:
            if alias in tool_def:
                return tool_def[alias]
        return default
    if hasattr(tool_def, field):
        return getattr(tool_def, field)
    for alias in aliases:
        if hasattr(tool_def, alias):
            return getattr(tool_def, alias)
    return default


def _normalize_risk_level(value: Any) -> RiskLevelName:
    if hasattr(value, "value"):
        value = value.value
    return str(value)


def _normalize_capability_kind(value: Any) -> CapabilityKind:
    if isinstance(value, CapabilityKind):
        return value
    if hasattr(value, "value"):
        value = value.value
    try:
        return CapabilityKind(str(value))
    except ValueError:
        return CapabilityKind.TOOL


__all__ = ["MCPTool", "MCPToolProvider"]
