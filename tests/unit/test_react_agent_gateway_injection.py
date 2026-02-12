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
