"""Unit tests for MCP tool provider schema mapping."""

from __future__ import annotations

from typing import Any

import pytest

from dare_framework.mcp.tool_provider import MCPToolProvider
from dare_framework.tool.types import ToolResult


class _FakeMCPClient:
    def __init__(self, name: str, tools: list[dict[str, Any]]) -> None:
        self._name = name
        self._tools = tools
        self.calls: list[tuple[str, dict[str, Any]]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return "http"

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def list_tools(self) -> list[dict[str, Any]]:
        return list(self._tools)

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: Any,
    ) -> ToolResult:
        self.calls.append((tool_name, dict(arguments)))
        return ToolResult(success=True, output={"ok": True}, error=None, evidence=[])


@pytest.mark.asyncio
async def test_mcp_tool_provider_reads_camel_case_schema_fields() -> None:
    input_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "result": {"type": "number"},
        },
        "required": ["result"],
    }
    client = _FakeMCPClient(
        "local_math",
        [
            {
                "name": "add",
                "description": "Add two numbers.",
                "inputSchema": input_schema,
                "outputSchema": output_schema,
            }
        ],
    )
    provider = MCPToolProvider([client])

    await provider.initialize()
    tools = provider.list_tools()

    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "local_math:add"
    assert tool.input_schema == input_schema
    assert tool.output_schema == output_schema


@pytest.mark.asyncio
async def test_mcp_tool_execute_forwards_arguments() -> None:
    client = _FakeMCPClient(
        "local_math",
        [
            {
                "name": "multiply",
                "description": "Multiply two numbers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            }
        ],
    )
    provider = MCPToolProvider([client])
    await provider.initialize()
    tool = provider.list_tools()[0]

    result = await tool.execute({"a": 6, "b": 7}, context=None)

    assert result.success is True
    assert client.calls == [("multiply", {"a": 6, "b": 7})]
