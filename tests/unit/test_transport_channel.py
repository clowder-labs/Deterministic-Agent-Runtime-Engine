import asyncio
import inspect

import pytest

from dare_framework.transport import AgentChannel, EnvelopeKind, TransportEnvelope, new_envelope_id
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


def _envelope(payload: str = "ping") -> TransportEnvelope:
    return TransportEnvelope(id=new_envelope_id(), payload=payload)


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

    async def invoke(self, action: ResourceAction, _params: dict[str, object]):
        self._calls.append(action.value)
        return {"ok": True}


class SlowActionHandler(IActionHandler):
    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.TOOLS_LIST}

    async def invoke(self, _action: ResourceAction, _params: dict[str, object]):
        await asyncio.sleep(0.2)
        return {"ok": True}


@pytest.mark.asyncio
async def test_outbox_backpressure_blocks() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, max_outbox=1, max_inbox=1)

    await channel.send(_envelope("one"))
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel.send(_envelope("two")), timeout=0.1)


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
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client, max_outbox=10)

    await channel.send(_envelope("one"))
    await channel.send(_envelope("two"))
    await channel.stop()

    assert channel._outbox.empty()


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
            payload="tools:list",
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
            payload="interrupt",
        )
    )

    assert fake_agent.interrupted is True
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel.poll(), timeout=0.1)


@pytest.mark.asyncio
async def test_invalid_control_payload_returns_structured_error() -> None:
    seen: list[TransportEnvelope] = []
    sent = asyncio.Event()

    async def receiver(msg: TransportEnvelope) -> None:
        seen.append(msg)
        sent.set()

    client = DummyClientChannel(receiver)
    channel = AgentChannel.build(client)
    channel.add_agent_control_handler(AgentControlHandler(FakeAgent()))
    await channel.start()
    try:
        sender = client.sender
        assert sender is not None
        await sender(
            TransportEnvelope(
                id="req-control-1",
                kind=EnvelopeKind.CONTROL,
                payload={"bad": "payload"},
            )
        )
        await asyncio.wait_for(sent.wait(), timeout=1.0)
    finally:
        await channel.stop()

    assert len(seen) == 1
    payload = seen[0].payload
    assert isinstance(payload, dict)
    assert payload.get("type") == "error"
    assert payload.get("kind") == "control"
    assert payload.get("ok") is False
    assert payload.get("code") == "INVALID_CONTROL_PAYLOAD"
    assert isinstance(payload.get("reason"), str)


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
                payload="tools:list",
            )
        )
        await asyncio.wait_for(sent.wait(), timeout=1.0)
        await sender(
            TransportEnvelope(
                id="req-message-after-timeout",
                kind=EnvelopeKind.MESSAGE,
                payload="hello-after-timeout",
            )
        )
        msg = await asyncio.wait_for(channel.poll(), timeout=1.0)
    finally:
        await channel.stop()

    assert msg.payload == "hello-after-timeout"
    timeout_payload = seen[0].payload
    assert isinstance(timeout_payload, dict)
    assert timeout_payload.get("type") == "error"
    assert timeout_payload.get("kind") == "action"
    assert timeout_payload.get("ok") is False
    assert timeout_payload.get("code") == "ACTION_TIMEOUT"
    assert isinstance(timeout_payload.get("reason"), str)
