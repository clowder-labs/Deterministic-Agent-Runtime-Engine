from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.infra.component import ComponentType
from dare_framework.plan.types import Envelope
from dare_framework.tool.default_tool_manager import ToolManager
from dare_framework.tool.types import ToolResult


class DummyModelAdapter(IModelAdapter):
    @property
    def name(self) -> str:
        return "dummy"

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

    async def execute(self, input: dict[str, Any], context: Any) -> ToolResult:
        return ToolResult(success=True, output=input)


class ListProvider:
    def __init__(self, tools: list[EchoTool]) -> None:
        self._tools = tools

    def list_tools(self) -> list[EchoTool]:
        return list(self._tools)


@pytest.mark.asyncio
async def test_agent_builder_minimal_build() -> None:
    agent = BaseAgent.simple_chat_agent_builder("test-agent").with_model(DummyModelAdapter()).build()

    result = await agent.run("hello")

    assert result.success is True
    assert result.output == "ok"


def test_agent_builder_derives_tool_defs_from_gateway() -> None:
    agent = (
        BaseAgent.simple_chat_agent_builder("tool-agent")
        .with_model(DummyModelAdapter())
        .add_tools(EchoTool())
        .build()
    )

    tools = agent.context.listing_tools()

    assert tools
    tool_def = tools[0]
    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == tool_def["capability_id"]
    assert tool_def["function"]["name"] == "echo"
    assert tool_def["function"]["parameters"] == EchoTool.input_schema
    assert tool_def.get("metadata", {}).get("display_name") == "echo"


@pytest.mark.asyncio
async def test_tool_manager_aggregates_and_enforces_allowlist() -> None:
    gateway = ToolManager()

    tool_a = EchoTool("echo_a")
    tool_b = EchoTool("echo_b")
    gateway.register_provider(ListProvider([tool_a]))
    gateway.register_provider(ListProvider([tool_b]))

    capabilities = await gateway.list_capabilities()
    assert len(capabilities) == 2
    cap_ids = [cap.id for cap in capabilities]

    allowed = Envelope(allowed_capability_ids=[cap_ids[0]])
    result = await gateway.invoke(cap_ids[0], {"value": 1}, envelope=allowed)
    assert isinstance(result, ToolResult)
    assert result.success is True

    with pytest.raises(PermissionError):
        await gateway.invoke(cap_ids[1], {}, envelope=allowed)
