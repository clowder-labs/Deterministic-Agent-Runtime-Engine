from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import DareAgent, ReactAgent, SimpleChatAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import RunResult
from dare_framework.tool.types import ToolResult


class _Model:
    name = "mock-model"

    def __init__(self, *, content: str = "ok", usage: dict[str, Any] | None = None) -> None:
        self._content = content
        self._usage = usage

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(content=self._content, tool_calls=[], usage=self._usage)


class _ToolGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=True, output={"ok": True})


class _RepeatingToolModelWithUsage:
    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(
            content="still searching",
            tool_calls=[
                {
                    "id": "tc_same",
                    "name": "tool:echo",
                    "arguments": {"value": "ping"},
                }
            ],
            usage={"total_tokens": 3},
        )


class _UniqueToolCallModelWithUsage:
    def __init__(self) -> None:
        self._round = 0

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        self._round += 1
        return ModelResponse(
            content="still searching",
            tool_calls=[
                {
                    "id": f"tc_{self._round}",
                    "name": "tool:echo",
                    "arguments": {"value": self._round},
                }
            ],
            usage={"total_tokens": self._round},
        )


class _ToolThenFinalWithoutUsageModel:
    def __init__(self) -> None:
        self._responses = [
            ModelResponse(
                content="calling tool",
                tool_calls=[
                    {
                        "id": "tc_1",
                        "name": "tool:echo",
                        "arguments": {"value": "ping"},
                    }
                ],
                usage={"total_tokens": 5},
            ),
            ModelResponse(content="final response", tool_calls=[], usage=None),
        ]
        self._idx = 0

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        response = self._responses[self._idx]
        self._idx += 1
        return response


def _assert_output_envelope(result: RunResult) -> dict[str, Any]:
    assert isinstance(result.output, dict)
    envelope = result.output
    assert set(envelope.keys()) == {"content", "metadata", "usage"}
    assert isinstance(envelope["content"], str)
    assert isinstance(envelope["metadata"], dict)
    assert envelope["usage"] is None or isinstance(envelope["usage"], dict)
    assert result.output_text == envelope["content"]
    return envelope


@pytest.mark.asyncio
async def test_simple_chat_returns_output_envelope() -> None:
    agent = SimpleChatAgent(
        name="simple-output-envelope",
        model=_Model(content="simple-ok", usage={"total_tokens": 7}),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert envelope["content"] == "simple-ok"
    assert envelope["usage"] == {"total_tokens": 7}


@pytest.mark.asyncio
async def test_react_agent_returns_output_envelope() -> None:
    agent = ReactAgent(
        name="react-output-envelope",
        model=_Model(content="react-ok"),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert envelope["content"] == "react-ok"
    assert envelope["usage"] is None


@pytest.mark.asyncio
async def test_react_agent_preserves_usage_in_output_envelope() -> None:
    agent = ReactAgent(
        name="react-output-envelope-usage",
        model=_Model(content="react-ok", usage={"total_tokens": 13}),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert envelope["content"] == "react-ok"
    assert envelope["usage"] == {"total_tokens": 13}


@pytest.mark.asyncio
async def test_react_agent_loop_guard_preserves_usage_in_output_envelope() -> None:
    agent = ReactAgent(
        name="react-output-envelope-loop-guard-usage",
        model=_RepeatingToolModelWithUsage(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
        max_tool_rounds=10,
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert "连续重复调用相同工具" in envelope["content"]
    assert envelope["usage"] == {"total_tokens": 3}


@pytest.mark.asyncio
async def test_react_agent_max_rounds_preserves_usage_in_output_envelope() -> None:
    agent = ReactAgent(
        name="react-output-envelope-max-rounds-usage",
        model=_UniqueToolCallModelWithUsage(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
        max_tool_rounds=2,
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert "达到最大轮次" in envelope["content"]
    assert envelope["usage"] == {"total_tokens": 2}


@pytest.mark.asyncio
async def test_react_agent_final_reply_without_usage_keeps_latest_usage() -> None:
    agent = ReactAgent(
        name="react-output-envelope-final-no-usage",
        model=_ToolThenFinalWithoutUsageModel(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert envelope["content"] == "final response"
    assert envelope["usage"] == {"total_tokens": 5}


@pytest.mark.asyncio
async def test_dare_agent_returns_output_envelope() -> None:
    agent = DareAgent(
        name="dare-output-envelope",
        model=_Model(content="dare-ok", usage={"total_tokens": 11}),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert envelope["content"] == "dare-ok"
    assert envelope["usage"] == {"total_tokens": 11}


@pytest.mark.asyncio
async def test_dare_agent_preserves_empty_content_in_output_envelope() -> None:
    agent = DareAgent(
        name="dare-output-envelope-empty",
        model=_Model(content=""),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    result = await agent("hello")
    envelope = _assert_output_envelope(result)
    assert envelope["content"] == ""
