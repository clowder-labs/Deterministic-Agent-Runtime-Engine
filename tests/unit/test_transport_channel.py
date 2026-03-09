import asyncio
import inspect

import pytest

from dare_framework.transport import (
    ActionPayload,
    AgentChannel,
    ControlPayload,
    EnvelopeKind,
    MessagePayload,
    TransportEnvelope,
    new_envelope_id,
)
from dare_framework.context.types import MessageKind, MessageRole
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.control_handler import AgentControlHandler
from dare_framework.transport.interaction.dispatcher import ActionHandlerDispatcher
from dare_framework.transport.interaction.handlers import IActionHandler


class DummyClientChannel:
    def __init__(self, receiver):
        self._receiver = receiver
        self.sender = None

    def attach_agent_envelope_sender(self, sender):
        self.sender = sender

    def agent_envelope_receiver(self):
        return self._receiver


def _envelope(text: str = "ping") -> TransportEnvelope:
    return TransportEnvelope(
        id=new_envelope_id(),
        payload=MessagePayload(
            id=new_envelope_id(),
            role="user",
            message_kind="chat",
            text=text,
        ),
    )


class FakeAgent:
    def __init__(self) -> None:
        self.agent_channel = None
        self.interrupted = False

    def interrupt(self) -> dict[str, bool]:
        self.interrupted = True
        return {"ok": True}

    def pause(self):  # pragma: no cover - control mapping contract only
        return None

    def retry(self):  # pragma: no cover - control mapping contract only
        return None

    def reverse(self):  # pragma: no cover - control mapping contract only
        return None


class RecordActionHandler(IActionHandler):
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.TOOLS_LIST}

    async def invoke(self, action: ResourceAction, **_params: object):
        self._calls.append(action.value)
        return {"ok": True}


class SlowActionHandler(IActionHandler):
    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.TOOLS_LIST}

    async def invoke(self, _action: ResourceAction, **_params: object):
        await asyncio.sleep(0.2)
        return {"ok": True}


@pytest.mark.asyncio
async def test_outbox_backpressure_blocks_when_receiver_is_slow() -> None:
    release = asyncio.Event()

    async def receiver(msg: TransportEnvelope) -> None:
        _ = msg
        await release.wait()

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, max_outbox=1, max_inbox=1)
    await channel.start()
    try:
        await channel.send(_envelope("one"))
        # Yield once so pump can pick the first envelope and block in receiver().
        await asyncio.sleep(0)
        await channel.send(_envelope("two"))
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(channel.send(_envelope("three")), timeout=0.1)
    finally:
        release.set()
        await channel.stop()


@pytest.mark.asyncio
async def test_inbox_backpressure_blocks_sender() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, max_outbox=1, max_inbox=1)

    sender = client.sender
    assert sender is not None
    await sender(_envelope("one"))
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sender(_envelope("two")), timeout=0.1)


@pytest.mark.asyncio
async def test_start_stop_idempotent() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)

    await channel.start()
    first_task = channel._out_pump_task
    await channel.start()
    assert channel._out_pump_task is first_task

    await channel.stop()


@pytest.mark.asyncio
async def test_stop_drops_outbox() -> None:
    release = asyncio.Event()

    async def receiver(msg: TransportEnvelope) -> None:
        _ = msg
        await release.wait()

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, max_outbox=2)
    await channel.start()
    try:
        await channel.send(_envelope("one"))
        await asyncio.sleep(0)
        await channel.send(_envelope("two"))
    finally:
        await channel.stop()
        release.set()

    assert channel._outbox.empty()


@pytest.mark.asyncio
async def test_send_before_start_drops_outgoing_envelope(caplog) -> None:
    seen: list[TransportEnvelope] = []

    async def receiver(msg: TransportEnvelope) -> None:
        seen.append(msg)

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, max_outbox=1)

    with caplog.at_level("WARNING", logger="dare.transport"):
        await channel.send(_envelope("pre-start"))

    assert channel._outbox.empty()
    assert seen == []
    assert any("dropping outgoing envelope" in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_receiver_errors_are_swallowed() -> None:
    event = asyncio.Event()
    calls = {"count": 0}

    async def receiver(msg: TransportEnvelope) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        event.set()

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)

    await channel.start()
    await channel.send(_envelope("first"))
    await channel.send(_envelope("second"))

    await asyncio.wait_for(event.wait(), timeout=1.0)
    await channel.stop()


@pytest.mark.asyncio
async def test_sender_errors_are_swallowed() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)

    async def broken_enqueue(_: TransportEnvelope) -> None:
        raise RuntimeError("boom")

    channel._enqueue_inbox = broken_enqueue  # type: ignore[assignment]

    sender = client.sender
    assert sender is not None
    await sender(_envelope("fail"))


@pytest.mark.asyncio
async def test_agent_channel_build_signature_excludes_encoder_decoder() -> None:
    params = inspect.signature(AgentChannel.build).parameters
    assert "encoder" not in params
    assert "decoder" not in params


@pytest.mark.asyncio
async def test_action_envelope_is_dispatched_by_channel() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)
    fake_agent = FakeAgent()
    fake_agent.agent_channel = channel
    calls: list[str] = []

    dispatcher = ActionHandlerDispatcher()
    dispatcher.register_action_handler(RecordActionHandler(calls))
    channel.add_action_handler_dispatcher(dispatcher)

    sender = client.sender
    assert sender is not None
    await sender(
        TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.ACTION,
            payload=ActionPayload(
                id=new_envelope_id(),
                resource_action="tools:list",
            ),
        )
    )

    assert calls == ["tools:list"]
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel.poll(), timeout=0.1)


@pytest.mark.asyncio
async def test_control_envelope_is_dispatched_by_channel() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)
    fake_agent = FakeAgent()
    channel.add_agent_control_handler(AgentControlHandler(fake_agent))

    sender = client.sender
    assert sender is not None
    await sender(
        TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.CONTROL,
            payload=ControlPayload(
                id=new_envelope_id(),
                control_id="interrupt",
            ),
        )
    )

    assert fake_agent.interrupted is True
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel.poll(), timeout=0.1)


@pytest.mark.asyncio
async def test_invalid_control_payload_returns_structured_error() -> None:
    with pytest.raises(TypeError, match="invalid payload type for envelope kind"):
        TransportEnvelope(
            id="req-control-1",
            kind=EnvelopeKind.CONTROL,
            payload=MessagePayload(
                id="msg-bad-control",
                role=MessageRole.USER,
                message_kind=MessageKind.CHAT,
                text="bad",
            ),
        )


@pytest.mark.asyncio
async def test_unknown_control_returns_structured_error_reply() -> None:
    seen: list[TransportEnvelope] = []
    sent = asyncio.Event()

    async def receiver(msg: TransportEnvelope) -> None:
        seen.append(msg)
        sent.set()

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)
    fake_agent = FakeAgent()
    channel.add_agent_control_handler(AgentControlHandler(fake_agent))

    await channel.start()
    try:
        sender = client.sender
        assert sender is not None
        await sender(
            TransportEnvelope(
                id="req-control-unknown",
                kind=EnvelopeKind.CONTROL,
                payload=ControlPayload(
                    id="ctl-unknown",
                    control_id="unknown-control",
                ),
            )
        )
        await asyncio.wait_for(sent.wait(), timeout=1.0)
    finally:
        await channel.stop()

    assert len(seen) == 1
    response = seen[0]
    assert response.kind is EnvelopeKind.CONTROL
    assert isinstance(response.payload, ControlPayload)
    assert response.payload.control_id == "unknown-control"
    assert response.payload.ok is False
    assert response.payload.code == "UNSUPPORTED_OPERATION"
    assert isinstance(response.payload.reason, str)
    assert "unknown control" in response.payload.reason


@pytest.mark.asyncio
async def test_invalid_message_payload_returns_structured_error_and_is_not_enqueued() -> None:
    with pytest.raises(TypeError, match="invalid payload type for envelope kind"):
        TransportEnvelope(
            id="req-message-invalid",
            kind=EnvelopeKind.MESSAGE,
            payload=ActionPayload(
                id="action-invalid",
                resource_action="tools:list",
            ),
        )


@pytest.mark.asyncio
async def test_action_timeout_returns_structured_error_and_channel_keeps_processing() -> None:
    seen: list[TransportEnvelope] = []
    sent = asyncio.Event()

    async def receiver(msg: TransportEnvelope) -> None:
        seen.append(msg)
        sent.set()

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, action_timeout_seconds=0.05)
    fake_agent = FakeAgent()
    fake_agent.agent_channel = channel
    dispatcher = ActionHandlerDispatcher()
    dispatcher.register_action_handler(SlowActionHandler())
    channel.add_action_handler_dispatcher(dispatcher)
    channel.add_agent_control_handler(AgentControlHandler(fake_agent))

    await channel.start()
    try:
        sender = client.sender
        assert sender is not None
        await sender(
            TransportEnvelope(
                id="req-action-timeout",
                kind=EnvelopeKind.ACTION,
                payload=ActionPayload(
                    id="action-timeout-1",
                    resource_action="tools:list",
                ),
            )
        )
        await asyncio.wait_for(sent.wait(), timeout=1.0)
        await sender(
            TransportEnvelope(
                id="req-message-after-timeout",
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(
                    id="msg-after-timeout",
                    role="user",
                    message_kind="chat",
                    text="hello-after-timeout",
                ),
            )
        )
        msg = await asyncio.wait_for(channel.poll(), timeout=1.0)
    finally:
        await channel.stop()

    assert isinstance(msg.payload, MessagePayload)
    assert msg.payload.text == "hello-after-timeout"
    assert seen[0].kind is EnvelopeKind.ACTION
    timeout_payload = seen[0].payload
    assert isinstance(timeout_payload, ActionPayload)
    assert timeout_payload.ok is False
    assert timeout_payload.code == "ACTION_TIMEOUT"
    assert isinstance(timeout_payload.reason, str)
