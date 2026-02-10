from __future__ import annotations

from typing import Any

import pytest

from dare_framework.config.types import Config
from dare_framework.mcp.action_handler import McpActionHandler
from dare_framework.transport.interaction.resource_action import ResourceAction


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"tool:{name}"
        self.input_schema = {"type": "object"}
        self.output_schema = {"type": "object"}


class _FakeMcpManager:
    def __init__(self) -> None:
        self._tools = {
            ("math", "add"): _FakeTool("math:add"),
        }
        self.reload_calls: list[str | None] = []

    def list_mcp_names(self, *, include_disabled: bool = False) -> list[str]:
        return ["math"]

    def list_tools(self, mcp_name: str | None = None) -> list[Any]:
        if mcp_name is None:
            return [self._tools[("math", "add")]]
        if mcp_name == "math":
            return [self._tools[("math", "add")]]
        return []

    def get_tool(self, mcp_name: str, tool_name: str) -> Any | None:
        if tool_name == "math:add":
            tool_name = "add"
        return self._tools.get((mcp_name, tool_name))

    async def reload(self, mcp_name: str | None = None) -> None:
        self.reload_calls.append(mcp_name)


@pytest.mark.asyncio
async def test_mcp_action_handler_supports_show_tool_and_queries_by_mcp_and_tool() -> None:
    handler = McpActionHandler(
        config=Config(mcp={"math": {}}),
        manager=None,
        mcp_manager=_FakeMcpManager(),
    )

    assert ResourceAction.MCP_SHOW_TOOL in handler.supports()

    result = await handler.invoke(
        ResourceAction.MCP_SHOW_TOOL,
        mcp_name="math",
        tool_name="add",
    )

    assert result["tool"]["name"] == "math:add"
    assert result["tool"]["description"] == "tool:math:add"


@pytest.mark.asyncio
async def test_mcp_action_handler_list_can_filter_tools_by_mcp_name() -> None:
    handler = McpActionHandler(
        config=Config(mcp={"math": {}}),
        manager=None,
        mcp_manager=_FakeMcpManager(),
    )

    result = await handler.invoke(ResourceAction.MCP_LIST, mcp_name="math")

    assert result["mcps"] == ["math"]
    assert result["tools"]
    assert result["tools"][0]["name"] == "math:add"


@pytest.mark.asyncio
async def test_mcp_action_handler_supports_reload_and_dispatches_to_manager() -> None:
    manager = _FakeMcpManager()
    handler = McpActionHandler(
        config=Config(mcp={"math": {}}),
        manager=None,
        mcp_manager=manager,
    )

    assert ResourceAction.MCP_RELOAD in handler.supports()

    result = await handler.invoke(ResourceAction.MCP_RELOAD, mcp_name="math")

    assert result["ok"] is True
    assert result["reloaded"] == "math"
    assert manager.reload_calls == ["math"]
