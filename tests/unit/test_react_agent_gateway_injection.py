from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent.react_agent import ReactAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.context.types import MessageKind
from dare_framework.context.smartcontext import SmartContext
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


class _UniqueToolLoopModel:
    def __init__(self) -> None:
        self._idx = 0

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        self._idx += 1
        return ModelResponse(
            content="still searching",
            tool_calls=[
                {
                    "id": f"tc_{self._idx}",
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


class _RecordingTransport:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send(self, envelope: Any) -> None:
        self.sent.append(envelope)


class _ThinkingSequenceModel:
    def __init__(self) -> None:
        self._responses = [
            ModelResponse(
                content="calling tool",
                thinking_content="need tool data",
                tool_calls=[
                    {
                        "id": "tc_1",
                        "name": "tool:echo",
                        "arguments": {"value": "ping"},
                    }
                ],
            ),
            ModelResponse(content="final answer", tool_calls=[]),
        ]
        self._idx = 0

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        response = self._responses[self._idx]
        self._idx += 1
        return response


class _CompressionRecordingContext(Context):
    def __init__(self, *, config: Config) -> None:
        super().__init__(config=config)
        self.compress_calls: list[dict[str, Any]] = []

    def compress(self, **options: Any) -> None:
        self.compress_calls.append(dict(options))
        super().compress(**options)


class _CompressionRecordingSmartContext(SmartContext):
    def __init__(self, *, config: Config) -> None:
        super().__init__(config=config)
        self.compress_calls: list[dict[str, Any]] = []

    def compress(self, **options: Any) -> None:
        self.compress_calls.append(dict(options))
        super().compress(**options)


class _FinalOnlyModel:
    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(content="final", tool_calls=[])


class _NonConvergingToolModel:
    def __init__(self) -> None:
        self._idx = 0

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        _ = (model_input, options)
        self._idx += 1
        return ModelResponse(
            content="keep going",
            tool_calls=[
                {
                    "id": f"tc_{self._idx}",
                    "name": "tool:echo",
                    "arguments": {"value": f"ping-{self._idx}"},
                }
            ],
        )


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
    assert len(injected_gateway.invoke_calls) == 1
    capability_id, params = injected_gateway.invoke_calls[0]
    assert capability_id == "tool:echo"
    assert params["value"] == "ping"
    assert params["context"] is context
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


@pytest.mark.asyncio
async def test_react_agent_emits_intermediate_transport_events_in_order() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")
    transport = _RecordingTransport()

    agent = ReactAgent(
        name="react-test-transport-events",
        model=_ThinkingSequenceModel(),
        context=context,
        tool_gateway=gateway,
    )

    result = await agent.execute("test", transport=transport)

    assert result.success is True
    message_kinds = [envelope.payload.message_kind for envelope in transport.sent]
    assert message_kinds == [
        MessageKind.THINKING,
        MessageKind.TOOL_CALL,
        MessageKind.TOOL_RESULT,
        MessageKind.CHAT,
    ]
    payloads = [envelope.payload for envelope in transport.sent]
    assert payloads[0].data == {"target": "model"}
    assert payloads[1].data["name"] == "tool:echo"
    assert payloads[2].data["success"] is True
    assert payloads[3].text == "final answer"


@pytest.mark.asyncio
async def test_react_agent_transport_loop_emits_single_terminal_result_event() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")
    transport = _RecordingTransport()

    agent = ReactAgent(
        name="react-test-transport-loop-terminal",
        model=_ThinkingSequenceModel(),
        context=context,
        tool_gateway=gateway,
        agent_channel=transport,
    )

    await agent._execute_polled_message(
        "test",
        channel=transport,
        envelope_id="req_1",
    )

    message_kinds = [envelope.payload.message_kind for envelope in transport.sent]
    assert message_kinds == [
        MessageKind.THINKING,
        MessageKind.TOOL_CALL,
        MessageKind.TOOL_RESULT,
        MessageKind.CHAT,
    ]

    terminal_payload = transport.sent[-1].payload
    assert terminal_payload.data["success"] is True
    assert terminal_payload.data["output"]["content"] == "final answer"


@pytest.mark.asyncio
async def test_react_agent_emits_terminal_message_for_repeated_tool_guard() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")
    transport = _RecordingTransport()

    agent = ReactAgent(
        name="react-test-loop-guard-terminal",
        model=_RepeatingToolModel(),
        context=context,
        tool_gateway=gateway,
    )

    result = await agent.execute("test", transport=transport)

    assert result.success is True
    assert transport.sent
    last_envelope = transport.sent[-1]
    assert last_envelope.payload.message_kind is MessageKind.CHAT
    assert "连续重复调用相同工具" in str(last_envelope.payload.data["output"])


@pytest.mark.asyncio
async def test_react_agent_emits_terminal_message_for_max_round_exit() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")
    transport = _RecordingTransport()

    agent = ReactAgent(
        name="react-test-max-round-terminal",
        model=_UniqueToolLoopModel(),
        context=context,
        tool_gateway=gateway,
        max_tool_rounds=2,
    )

    result = await agent.execute("test", transport=transport)

    assert result.success is True
    assert transport.sent
    last_envelope = transport.sent[-1]
    assert last_envelope.payload.message_kind is MessageKind.CHAT
    assert "达到最大轮次" in str(last_envelope.payload.data["output"])


@pytest.mark.asyncio
async def test_react_agent_auto_compress_triggers_before_model_call() -> None:
    context = _CompressionRecordingContext(config=Config())
    context.budget.max_tokens = 100
    gateway = _RecordingGateway("injected")
    agent = ReactAgent(
        name="react-test-auto-compress",
        model=_FinalOnlyModel(),
        context=context,
        tool_gateway=gateway,
        auto_compress=True,
        compress_trigger_ratio=0.01,
        compress_target_ratio=0.5,
    )

    result = await agent("test auto compress trigger")

    assert result.success is True
    assert len(context.compress_calls) >= 1
    first_call = context.compress_calls[0]
    assert first_call.get("tool_pair_safe") is True
    assert first_call.get("target_tokens") is not None


@pytest.mark.asyncio
async def test_react_agent_auto_compress_nan_ratios_fallback_to_defaults() -> None:
    context = _CompressionRecordingContext(config=Config())
    context.budget.max_tokens = 100
    gateway = _RecordingGateway("injected")
    agent = ReactAgent(
        name="react-test-auto-compress-nan-ratios",
        model=_FinalOnlyModel(),
        context=context,
        tool_gateway=gateway,
        auto_compress=True,
        compress_trigger_ratio=float("nan"),
        compress_target_ratio=float("nan"),
    )

    result = await agent("x" * 600)

    assert result.success is True
    assert len(context.compress_calls) >= 1
    first_call = context.compress_calls[0]
    assert first_call.get("target_tokens") == 75


@pytest.mark.asyncio
async def test_react_agent_without_auto_compress_keeps_legacy_behavior() -> None:
    context = _CompressionRecordingContext(config=Config())
    gateway = _RecordingGateway("injected")
    agent = ReactAgent(
        name="react-test-no-auto-compress",
        model=_FinalOnlyModel(),
        context=context,
        tool_gateway=gateway,
        auto_compress=False,
    )

    result = await agent("test no auto compress")

    assert result.success is True
    assert context.compress_calls == []


@pytest.mark.asyncio
async def test_react_agent_auto_compress_triggers_in_smart_context_path() -> None:
    context = _CompressionRecordingSmartContext(config=Config())
    context.budget.max_tokens = 100
    gateway = _RecordingGateway("injected")
    agent = ReactAgent(
        name="react-test-smartcontext-auto-compress",
        model=_FinalOnlyModel(),
        context=context,
        tool_gateway=gateway,
        auto_compress=True,
        compress_trigger_ratio=0.01,
        compress_target_ratio=0.5,
    )

    result = await agent("smart context compress")

    assert result.success is True
    assert len(context.compress_calls) >= 1
    assert context.compress_calls[0].get("tool_pair_safe") is True


@pytest.mark.asyncio
async def test_react_agent_loop_guard_emits_terminal_message_event() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")
    transport = _RecordingTransport()
    agent = ReactAgent(
        name="react-test-loop-guard-terminal-message",
        model=_RepeatingToolModel(),
        context=context,
        tool_gateway=gateway,
        max_tool_rounds=10,
    )

    result = await agent.execute("test loop guard", transport=transport)

    assert result.success is True
    assert transport.sent[-1].payload.message_kind is MessageKind.CHAT
    assert "连续重复调用相同工具" in transport.sent[-1].payload.data["output"]


@pytest.mark.asyncio
async def test_react_agent_max_round_exit_emits_terminal_message_event() -> None:
    context = Context(config=Config())
    gateway = _RecordingGateway("injected")
    transport = _RecordingTransport()
    agent = ReactAgent(
        name="react-test-max-round-terminal-message",
        model=_NonConvergingToolModel(),
        context=context,
        tool_gateway=gateway,
        max_tool_rounds=2,
    )

    result = await agent.execute("test max rounds", transport=transport)

    assert result.success is True
    assert transport.sent[-1].payload.message_kind is MessageKind.CHAT
    assert "未收敛" in transport.sent[-1].payload.data["output"]
