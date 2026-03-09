from __future__ import annotations

import asyncio
from typing import Any

import pytest

from dare_framework.agent.base_agent import BaseAgent
from dare_framework.agent.status import AgentStatus
from dare_framework.plan.types import RunResult
from dare_framework.context.types import AttachmentRef, Message, MessageKind, MessageRole
from dare_framework.transport import EnvelopeKind, MessagePayload, TransportEnvelope


class _CaptureAgent(BaseAgent):
    def __init__(self, name: str, *, agent_channel: Any | None = None) -> None:
        super().__init__(name, agent_channel=agent_channel)
        self.seen_transport: Any | None = None
        self.seen_tasks: list[str] = []
        self.seen_inputs: list[Any] = []

    async def execute(self, task: Message, *, transport: Any = None) -> RunResult:
        task_text = task.text or ""
        self.seen_transport = transport
        self.seen_inputs.append(task)
        self.seen_tasks.append(task_text)
        if len(self.seen_tasks) >= 2:
            self._status = AgentStatus.STOPPED
        return RunResult(success=True, output=f"ok:{task_text}", output_text=f"ok:{task_text}")


class _StopAfterFirstAgent(BaseAgent):
    def __init__(self, name: str, *, agent_channel: Any | None = None) -> None:
        super().__init__(name, agent_channel=agent_channel)
        self.seen_tasks: list[str] = []
        self.seen_inputs: list[Any] = []

    async def execute(self, task: Message, *, transport: Any = None) -> RunResult:
        _ = transport
        task_text = task.text or ""
        self.seen_inputs.append(task)
        self.seen_tasks.append(task_text)
        self._status = AgentStatus.STOPPED
        return RunResult(success=True, output=f"ok:{task_text}", output_text=f"ok:{task_text}")


class _BatchPollingChannel:
    def __init__(self) -> None:
        self._sent: list[TransportEnvelope] = []
        self._polled = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> list[TransportEnvelope]:
        if self._polled:
            await asyncio.sleep(10)
            return []
        self._polled = True
        return [
            TransportEnvelope(
                id="m1",
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(id="msg-1", role="user", message_kind="chat", text="first"),
            ),
            TransportEnvelope(
                id="m2",
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(id="msg-2", role="user", message_kind="chat", text="second"),
            ),
        ]

    async def send(self, msg: TransportEnvelope) -> None:
        self._sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


class _InvalidPayloadBatchChannel:
    def __init__(self) -> None:
        self._sent: list[TransportEnvelope] = []
        self._polled = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> list[TransportEnvelope]:
        if self._polled:
            await asyncio.sleep(10)
            return []
        self._polled = True
        return [
            TransportEnvelope(
                id="bad",
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(
                    id="msg-bad",
                    role=MessageRole.ASSISTANT,
                    message_kind=MessageKind.SUMMARY,
                    text="not a user prompt",
                ),
            ),
            TransportEnvelope(
                id="ok",
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(id="msg-ok", role=MessageRole.USER, message_kind=MessageKind.CHAT, text="valid"),
            ),
        ]

    async def send(self, msg: TransportEnvelope) -> None:
        self._sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


class _RecordingSendChannel:
    def __init__(self) -> None:
        self.sent: list[TransportEnvelope] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> TransportEnvelope:
        raise RuntimeError("not used")

    async def send(self, msg: TransportEnvelope) -> None:
        self.sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


class _SingleMessageChannel:
    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self._polled = False
        self._sent: list[TransportEnvelope] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> TransportEnvelope:
        if self._polled:
            await asyncio.sleep(10)
            return TransportEnvelope(
                id="idle",
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(id="msg-idle", role="user", message_kind="chat", text=""),
            )
        self._polled = True
        return TransportEnvelope(id="m1", kind=EnvelopeKind.MESSAGE, payload=self._payload)

    async def send(self, msg: TransportEnvelope) -> None:
        self._sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


class _ErroringAgent(BaseAgent):
    async def execute(self, task: Message, *, transport: Any = None) -> RunResult:
        _ = task
        _ = transport
        self._status = AgentStatus.STOPPED
        raise RuntimeError("simulated model timeout")


class _TransportLoopFlagProbeAgent(BaseAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.observed_loop_state: dict[str, bool] = {}
        self.loop_execution_started = asyncio.Event()
        self.allow_loop_execution_finish = asyncio.Event()

    async def execute(self, task: Message, *, transport: Any = None) -> RunResult:
        task_text = task.text or ""
        self.observed_loop_state[task_text] = self._is_transport_loop_execution(transport=transport)
        if task_text == "loop-task":
            self.loop_execution_started.set()
            await self.allow_loop_execution_finish.wait()
        return RunResult(success=True, output=task_text, output_text=task_text)


@pytest.mark.asyncio
async def test_public_surface_uses_call_not_run() -> None:
    agent = _CaptureAgent("capture-agent")
    assert not hasattr(agent, "run")
    assert hasattr(agent, "execute")


@pytest.mark.asyncio
async def test_call_with_no_transport_injects_noop_transport() -> None:
    agent = _CaptureAgent("capture-agent")

    result = await agent("hello")

    assert result.success is True
    assert agent.seen_transport is not None


@pytest.mark.asyncio
async def test_call_path_does_not_send_terminal_response_to_transport() -> None:
    agent = _CaptureAgent("capture-agent")
    transport = _RecordingSendChannel()

    result = await agent("hello", transport=transport)

    assert result.success is True
    assert transport.sent == []


@pytest.mark.asyncio
async def test_transport_loop_accepts_batched_messages_from_poll() -> None:
    channel = _BatchPollingChannel()
    agent = _CaptureAgent("batch-agent", agent_channel=channel)
    agent._status = AgentStatus.RUNNING

    await agent._run_transport_loop()

    assert agent.seen_tasks == ["first", "second"]
    assert len(channel._sent) == 2
    assert [envelope.reply_to for envelope in channel._sent] == ["m1", "m2"]
    assert all(envelope.kind is EnvelopeKind.MESSAGE for envelope in channel._sent)
    assert all(isinstance(envelope.payload, MessagePayload) for envelope in channel._sent)
    assert all(envelope.payload.message_kind is MessageKind.CHAT for envelope in channel._sent)


@pytest.mark.asyncio
async def test_transport_loop_preserves_canonical_message_payload() -> None:
    channel = _SingleMessageChannel(
        MessagePayload(
            id="msg-1",
            role=MessageRole.USER,
            message_kind=MessageKind.CHAT,
            text="look at these",
            attachments=[
                AttachmentRef(
                    uri="https://example.com/a.png",
                    mime_type="image/png",
                    filename="a.png",
                )
            ],
        )
    )
    agent = _StopAfterFirstAgent("capture-canonical-message", agent_channel=channel)
    agent._status = AgentStatus.RUNNING

    await agent._run_transport_loop()

    assert len(agent.seen_inputs) == 1
    captured = agent.seen_inputs[0]
    assert isinstance(captured, Message)
    assert captured.role is MessageRole.USER
    assert captured.kind is MessageKind.CHAT
    assert captured.text == "look at these"
    assert len(captured.attachments) == 1
    assert captured.attachments[0].uri == "https://example.com/a.png"


@pytest.mark.asyncio
async def test_transport_loop_returns_structured_error_for_invalid_message_payload() -> None:
    channel = _InvalidPayloadBatchChannel()
    agent = _StopAfterFirstAgent("invalid-payload-agent", agent_channel=channel)
    agent._status = AgentStatus.RUNNING

    await agent._run_transport_loop()

    assert agent.seen_tasks == ["valid"]
    error_payloads = [
        envelope.payload
        for envelope in channel._sent
        if envelope.kind is EnvelopeKind.MESSAGE
        and isinstance(envelope.payload, MessagePayload)
        and envelope.payload.message_kind is MessageKind.SUMMARY
    ]
    assert len(error_payloads) == 1
    payload = error_payloads[0]
    assert payload.data == {
        "success": False,
        "target": "prompt",
        "code": "INVALID_MESSAGE_PAYLOAD",
        "reason": "invalid message payload (expected MessagePayload)",
    }


@pytest.mark.asyncio
async def test_transport_loop_returns_structured_error_when_execute_raises() -> None:
    channel = _SingleMessageChannel(MessagePayload(id="msg-hello", role="user", message_kind="chat", text="hello"))
    agent = _ErroringAgent("erroring-agent", agent_channel=channel)
    agent._status = AgentStatus.RUNNING

    await agent._run_transport_loop()

    error_envelopes = [
        envelope
        for envelope in channel._sent
        if envelope.kind is EnvelopeKind.MESSAGE
        and isinstance(envelope.payload, MessagePayload)
        and envelope.payload.message_kind is MessageKind.SUMMARY
    ]
    assert len(error_envelopes) == 1
    error_envelope = error_envelopes[0]
    payload = error_envelope.payload
    assert isinstance(payload, MessagePayload)
    assert payload.data is not None
    assert payload.data.get("code") == "AGENT_EXECUTION_FAILED"
    assert "simulated model timeout" in str(payload.data.get("reason"))


@pytest.mark.asyncio
async def test_transport_loop_flag_is_task_local_for_concurrent_execute_calls() -> None:
    agent = _TransportLoopFlagProbeAgent("probe-agent")
    channel = _RecordingSendChannel()

    polled_task = asyncio.create_task(
        agent._execute_polled_message(
            "loop-task",
            channel=channel,
            envelope_id="req_1",
        )
    )
    await agent.loop_execution_started.wait()

    await agent.execute("direct-task", transport=channel)
    agent.allow_loop_execution_finish.set()
    await polled_task

    assert agent.observed_loop_state["loop-task"] is True
    assert agent.observed_loop_state["direct-task"] is False
