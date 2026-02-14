from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent.react_agent import ReactAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.types import CapabilityDescriptor, CapabilityType, ToolResult


class _SequenceModel:
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
            ),
            ModelResponse(content="final", tool_calls=[]),
        ]
        self._idx = 0

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        response = self._responses[self._idx]
        self._idx += 1
        return response


class _EmptyFinalModel:
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
            ),
            ModelResponse(content="", tool_calls=[]),
        ]
        self._idx = 0

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        response = self._responses[self._idx]
        self._idx += 1
        return response


class _RepeatingToolModel:
    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
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
        )


class _RecordingGateway:
    def __init__(self, label: str) -> None:
        self.label = label
        self.invoke_calls: list[tuple[str, dict[str, Any]]] = []
        self._capabilities = [
            CapabilityDescriptor(
                id="tool:echo",
                type=CapabilityType.TOOL,
                name="echo",
                description="echo",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )
        ]

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return list(self._capabilities)

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = envelope
        self.invoke_calls.append((capability_id, params))
        return ToolResult(success=True, output={"gateway": self.label, "params": params})


@pytest.mark.asyncio
async def test_react_agent_prefers_injected_gateway_over_context_gateway() -> None:
    context_gateway = _RecordingGateway("context")
    injected_gateway = _RecordingGateway("injected")
    context = Context(config=Config(), tool_gateway=context_gateway)

    agent = ReactAgent(
        name="react-test",
        model=_SequenceModel(),
        context=context,
        tool_gateway=injected_gateway,
    )

    result = await agent("test")

    assert result.success is True
    assert injected_gateway.invoke_calls == [("tool:echo", {"value": "ping"})]
    assert context_gateway.invoke_calls == []


@pytest.mark.asyncio
async def test_react_agent_returns_fallback_when_model_final_reply_is_empty() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")

    agent = ReactAgent(
        name="react-test-empty-final",
        model=_EmptyFinalModel(),
        context=context,
        tool_gateway=gateway,
    )

    result = await agent("test")

    assert result.success is True
    assert isinstance(result.output_text, str)
    assert result.output_text.strip() != ""
    assert "模型未返回可显示的文本回复" in result.output_text


@pytest.mark.asyncio
async def test_react_agent_stops_repeated_identical_tool_loop() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")

    agent = ReactAgent(
        name="react-test-loop-guard",
        model=_RepeatingToolModel(),
        context=context,
        tool_gateway=gateway,
        max_tool_rounds=10,
    )

    result = await agent("test")

    assert result.success is True
    assert "连续重复调用相同工具" in str(result.output_text)
    assert len(gateway.invoke_calls) == 2
