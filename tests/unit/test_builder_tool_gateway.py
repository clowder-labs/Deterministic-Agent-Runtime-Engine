from __future__ import annotations

from typing import Any

import pytest

from dare_framework.builder import Builder
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import Envelope
from dare_framework.tool._internal.gateway.default_tool_gateway import DefaultToolGateway
from dare_framework.infra.component import ComponentType
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityType,
    ProviderStatus,
    ToolResult,
)


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
    name = "echo"
    description = "Echo input text"
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
    output_schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    async def execute(self, input: dict[str, Any], context: Any) -> ToolResult:
        return ToolResult(success=True, output=input)


class FakeProvider:
    def __init__(self, capability: CapabilityDescriptor, payload: dict[str, Any]) -> None:
        self._capability = capability
        self._payload = payload

    async def list(self) -> list[CapabilityDescriptor]:
        return [self._capability]

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        return {"capability_id": capability_id, **self._payload, **params}

    async def health_check(self) -> ProviderStatus:
        return ProviderStatus.HEALTHY


@pytest.mark.asyncio
async def test_agent_builder_minimal_build() -> None:
    agent = Builder.simple_chat_agent_builder("test-agent").with_model(DummyModelAdapter()).build()

    result = await agent.run("hello")

    assert result.success is True
    assert result.output == "ok"


def test_agent_builder_derives_tool_defs_from_gateway() -> None:
    agent = (
        Builder.simple_chat_agent_builder("tool-agent")
        .with_model(DummyModelAdapter())
        .add_tools(EchoTool())
        .build()
    )

    tools = agent.context.listing_tools()

    assert tools
    tool_def = tools[0]
    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == "echo"
    assert tool_def["capability_id"] == "tool:echo"
    assert tool_def["function"]["parameters"] == EchoTool.input_schema


@pytest.mark.asyncio
async def test_default_tool_gateway_aggregates_and_enforces_allowlist() -> None:
    gateway = DefaultToolGateway()

    cap_a = CapabilityDescriptor(
        id="tool:a",
        type=CapabilityType.TOOL,
        name="a",
        description="tool a",
        input_schema={"type": "object", "properties": {}},
    )
    cap_b = CapabilityDescriptor(
        id="tool:b",
        type=CapabilityType.TOOL,
        name="b",
        description="tool b",
        input_schema={"type": "object", "properties": {}},
    )

    gateway.register_provider(FakeProvider(cap_a, {"ok": True}))
    gateway.register_provider(FakeProvider(cap_b, {"ok": True}))

    capabilities = await gateway.list_capabilities()
    assert {cap.id for cap in capabilities} == {"tool:a", "tool:b"}

    allowed = Envelope(allowed_capability_ids=["tool:a"])
    result = await gateway.invoke("tool:a", {"value": 1}, envelope=allowed)
    assert result["capability_id"] == "tool:a"

    with pytest.raises(PermissionError):
        await gateway.invoke("tool:b", {}, envelope=allowed)
