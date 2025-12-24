from __future__ import annotations

from typing import Iterable

from ..core.interfaces import IMCPClient, ITool
from ..core.models import RunContext, ToolDefinition, ToolResult, ToolRiskLevel
from .base_component import BaseComponent


class MCPTool(BaseComponent):
    def __init__(self, client: IMCPClient, definition: ToolDefinition) -> None:
        self._client = client
        self._definition = definition

    @property
    def name(self) -> str:
        return self._definition.name

    @property
    def description(self) -> str:
        return self._definition.description

    @property
    def input_schema(self) -> dict:
        return self._definition.input_schema

    @property
    def output_schema(self) -> dict:
        return self._definition.output_schema

    @property
    def risk_level(self):
        return self._definition.risk_level

    @property
    def tool_type(self):
        return self._definition.tool_type

    @property
    def requires_approval(self) -> bool:
        return self._definition.requires_approval

    @property
    def timeout_seconds(self) -> int:
        return self._definition.timeout_seconds

    @property
    def produces_assertions(self) -> list[dict]:
        return self._definition.produces_assertions

    @property
    def is_work_unit(self) -> bool:
        return self._definition.is_work_unit

    async def execute(self, input: dict, context: RunContext) -> ToolResult:
        return await self._client.call_tool(self._definition.name, input, context)


class MCPToolkit:
    def __init__(self, clients: Iterable[IMCPClient]):
        self._clients = list(clients)
        self._tools: list[MCPTool] = []

    async def initialize(self) -> None:
        for client in self._clients:
            await client.connect()
            for tool_def in await client.list_tools():
                self._tools.append(MCPTool(client, _coerce_risk(tool_def)))

    async def disconnect(self) -> None:
        for client in self._clients:
            await client.disconnect()

    def export_tools(self) -> list[ITool]:
        return list(self._tools)


def _coerce_risk(tool_def: ToolDefinition) -> ToolDefinition:
    if isinstance(tool_def.risk_level, ToolRiskLevel):
        return tool_def
    return ToolDefinition(
        name=tool_def.name,
        description=tool_def.description,
        input_schema=tool_def.input_schema,
        output_schema=tool_def.output_schema,
        tool_type=tool_def.tool_type,
        risk_level=ToolRiskLevel.READ_ONLY,
        requires_approval=tool_def.requires_approval,
        timeout_seconds=tool_def.timeout_seconds,
        produces_assertions=tool_def.produces_assertions,
        is_work_unit=tool_def.is_work_unit,
    )
