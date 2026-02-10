"""Unit tests for MCP tool provider integration."""

from __future__ import annotations

from typing import Any

import pytest

from dare_framework.mcp.tool_provider import MCPToolProvider
from dare_framework.tool.kernel import ITool
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.tool.types import CapabilityKind, RunContext, ToolResult, ToolType


class _FakeTool(ITool):
    def __init__(self, name: str, *, timeout_seconds: int = 30) -> None:
        self._name = name
        self._timeout_seconds = timeout_seconds
        self.calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"tool:{self._name}"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}

    @property
    def output_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"ok": {"type": "boolean"}}}

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(self, *, run_context: RunContext[Any], **params: Any) -> ToolResult[dict[str, Any]]:
        _ = run_context
        self.calls.append(dict(params))
        return ToolResult(success=True, output={"ok": True})


class _FakeMCPClient:
    def __init__(self, name: str, tools: list[ITool]) -> None:
        self._name = name
        self._tools = list(tools)
        self.connected = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return "http"

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def list_tools(self) -> list[ITool]:
        return list(self._tools)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any], context: Any) -> ToolResult:
        _ = tool_name, arguments, context
        return ToolResult(success=True, output={"ok": True}, error=None, evidence=[])


@pytest.mark.asyncio
async def test_mcp_tool_provider_lists_and_gets_tools() -> None:
    tool = _FakeTool("local_math:add")
    client = _FakeMCPClient("local_math", [tool])
    provider = MCPToolProvider([client])

    await provider.initialize()
    tools = provider.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "local_math:add"
    assert provider.get_tool("local_math", "add") is tool


@pytest.mark.asyncio
async def test_mcp_tool_execute_forwards_keyword_arguments() -> None:
    tool = _FakeTool("local_math:multiply")
    client = _FakeMCPClient("local_math", [tool])
    provider = MCPToolProvider([client])
    await provider.initialize()
    listed = provider.list_tools()

    result = await listed[0].execute(run_context=RunContext(None), a=6, b=7)

    assert result.success is True
    assert tool.calls == [{"a": 6, "b": 7}]


@pytest.mark.asyncio
async def test_mcp_tool_registers_timeout_metadata_via_tool_manager() -> None:
    tool = _FakeTool("local_math:divide", timeout_seconds=42)
    client = _FakeMCPClient("local_math", [tool])
    provider = MCPToolProvider([client])
    await provider.initialize()

    manager = ToolManager(load_entrypoints=False)
    manager.register_provider(provider)
    caps = manager.list_capabilities()
    assert caps
    metadata = caps[0].metadata or {}
    assert metadata.get("timeout_seconds") == 42
