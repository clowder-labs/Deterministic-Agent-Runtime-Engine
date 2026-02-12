from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.infra.component import ComponentType
from dare_framework.plan.types import Envelope
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.tool.tool_gateway import ToolGateway
from dare_framework.tool.types import ToolResult


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


class EchoTool:
    description = "Echo input text"
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
    output_schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    def __init__(self, name: str = "echo") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, *, run_context: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = run_context
        return ToolResult(success=True, output=params)


class ListProvider:
    def __init__(self, tools: list[EchoTool]) -> None:
        self._tools = tools

    def list_tools(self) -> list[EchoTool]:
        return list(self._tools)


@pytest.mark.asyncio
async def test_agent_builder_minimal_build() -> None:
    agent = await BaseAgent.simple_chat_agent_builder("test-agent").with_model(DummyModelAdapter()).build()

    result = await agent("hello")

    assert result.success is True
    assert result.output == "ok"
    assert result.output_text == "ok"


@pytest.mark.asyncio
async def test_agent_builder_derives_tool_defs_from_gateway() -> None:
    agent = await (
        BaseAgent.simple_chat_agent_builder("tool-agent")
        .with_model(DummyModelAdapter())
        .add_tools(EchoTool())
        .build()
    )

    tools = agent.context.list_tools()

    assert tools
    descriptor = tools[0]
    assert descriptor.id == "echo"
    assert descriptor.name == "echo"
    assert descriptor.description == EchoTool.description
    assert descriptor.input_schema == EchoTool.input_schema
    assert descriptor.metadata is not None
    assert descriptor.metadata.get("display_name") == "echo"


@pytest.mark.asyncio
async def test_tool_manager_aggregates_and_enforces_allowlist() -> None:
    manager = ToolManager()
    gateway = ToolGateway(manager)

    tool_a = EchoTool("echo_a")
    tool_b = EchoTool("echo_b")
    manager.register_provider(ListProvider([tool_a]))
    manager.register_provider(ListProvider([tool_b]))

    capabilities = manager.list_capabilities()
    assert len(capabilities) == 2
    cap_ids = [cap.id for cap in capabilities]

    allowed = Envelope(allowed_capability_ids=[cap_ids[0]])
    result = await gateway.invoke(cap_ids[0], envelope=allowed, value=1)
    assert isinstance(result, ToolResult)
    assert result.success is True

    with pytest.raises(PermissionError):
        await gateway.invoke(cap_ids[1], envelope=allowed)
