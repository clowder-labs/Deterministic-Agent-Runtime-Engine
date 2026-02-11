from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.agent.react_agent import ReactAgent
from dare_framework.agent.simple_chat import SimpleChatAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.types import ToolResult


class _DummyModel:
    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(content="ok", tool_calls=[])


class _DummyGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=True, output={})


def test_simple_chat_agent_requires_context_and_no_tools_alias() -> None:
    model = _DummyModel()
    gateway = _DummyGateway()

    with pytest.raises(TypeError):
        SimpleChatAgent(name="simple", model=model, tool_gateway=gateway)

    with pytest.raises(TypeError):
        SimpleChatAgent(
            name="simple",
            model=model,
            context=Context(config=Config(), tool_gateway=gateway),
            tools=gateway,
        )


def test_react_agent_requires_context() -> None:
    model = _DummyModel()
    gateway = _DummyGateway()

    with pytest.raises(TypeError):
        ReactAgent(name="react", model=model, tool_gateway=gateway)


def test_dare_agent_requires_context_and_tool_gateway() -> None:
    model = _DummyModel()
    context = Context(config=Config())

    with pytest.raises(TypeError):
        DareAgent(name="dare", model=model)

    with pytest.raises(TypeError):
        DareAgent(name="dare", model=model, context=context)
