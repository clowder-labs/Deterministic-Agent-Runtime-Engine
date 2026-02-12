from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config.types import Config
from dare_framework.context import Context
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.tool_manager import ToolManager


class DummyModelAdapter(IModelAdapter):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def model(self) -> str:
        return "dummy-model"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.MODEL_ADAPTER

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        return ModelResponse(content="ok")


class SpyMCPManager:
    def __init__(self) -> None:
        self.reload_calls: list[dict[str, Any]] = []
        self.unload_calls: list[Any] = []
        self.inspect_calls: list[dict[str, Any]] = []

    async def reload(
        self,
        tool_manager: Any,
        *,
        config: Config | None = None,
        paths: list[str | Path] | None = None,
    ) -> dict[str, Any]:
        self.reload_calls.append(
            {
                "tool_manager": tool_manager,
                "config": config,
                "paths": paths,
            }
        )
        return {"provider": "ok"}

    async def unload(self, tool_manager: Any) -> bool:
        self.unload_calls.append(tool_manager)
        return True

    def list_mcp_tool_defs(self, tool_manager: Any, *, tool_name: str | None = None) -> list[dict[str, Any]]:
        self.inspect_calls.append({"tool_manager": tool_manager, "tool_name": tool_name})
        return [{"function": {"name": "math:add"}}]


@pytest.mark.asyncio
async def test_dare_agent_reload_mcp_delegates_to_manager() -> None:
    gateway = ToolManager(load_entrypoints=False)
    mcp_manager = SpyMCPManager()
    agent = DareAgent(
        "agent",
        model=DummyModelAdapter(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        mcp_manager=mcp_manager,  # type: ignore[arg-type]
    )

    config = Config(mcp_paths=[".dare/mcp"])
    result = await agent.reload_mcp(config=config, paths=["/tmp/mcp"])

    assert result == {"provider": "ok"}
    assert len(mcp_manager.reload_calls) == 1
    assert mcp_manager.reload_calls[0]["tool_manager"] is gateway
    assert mcp_manager.reload_calls[0]["config"] == config
    assert mcp_manager.reload_calls[0]["paths"] == ["/tmp/mcp"]


@pytest.mark.asyncio
async def test_dare_agent_unload_mcp_delegates_to_manager() -> None:
    gateway = ToolManager(load_entrypoints=False)
    mcp_manager = SpyMCPManager()
    agent = DareAgent(
        "agent",
        model=DummyModelAdapter(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        mcp_manager=mcp_manager,  # type: ignore[arg-type]
    )

    removed = await agent.unload_mcp()

    assert removed is True
    assert mcp_manager.unload_calls == [gateway]


def test_dare_agent_inspect_mcp_tools_delegates_to_manager() -> None:
    gateway = ToolManager(load_entrypoints=False)
    mcp_manager = SpyMCPManager()
    agent = DareAgent(
        "agent",
        model=DummyModelAdapter(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        mcp_manager=mcp_manager,  # type: ignore[arg-type]
    )

    tool_defs = agent.inspect_mcp_tools(tool_name="math:add")

    assert tool_defs == [{"function": {"name": "math:add"}}]
    assert mcp_manager.inspect_calls == [{"tool_manager": gateway, "tool_name": "math:add"}]


@pytest.mark.asyncio
async def test_dare_agent_reload_mcp_requires_mcp_manager() -> None:
    gateway = ToolManager(load_entrypoints=False)
    agent = DareAgent(
        "agent",
        model=DummyModelAdapter(),
        context=Context(config=Config()),
        tool_gateway=gateway,
    )

    with pytest.raises(RuntimeError, match="MCP manager is not configured"):
        await agent.reload_mcp()


@pytest.mark.asyncio
async def test_dare_agent_reload_mcp_requires_manageable_tool_gateway() -> None:
    mcp_manager = SpyMCPManager()
    agent = DareAgent(
        "agent",
        model=DummyModelAdapter(),
        context=Context(config=Config()),
        tool_gateway=object(),  # type: ignore[arg-type]
        mcp_manager=mcp_manager,  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="Tool gateway does not support provider management"):
        await agent.reload_mcp()
