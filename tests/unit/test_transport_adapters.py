import asyncio

import pytest

from dare_framework.transport._internal.adapters import DirectClientChannel, StdioClientChannel, WebSocketClientChannel
from dare_framework.transport.types import EnvelopeKind, TransportEnvelope


@pytest.mark.asyncio
async def test_stdio_single_slash_maps_to_action_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[TransportEnvelope] = []
    stdio = StdioClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        sent.append(msg)

    stdio.attach_agent_envelope_sender(sender)

    lines = iter(["/", "/quit"])

    async def fake_to_thread(_fn, _prompt):
        return next(lines)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    await stdio.start()

    assert len(sent) == 1
    assert sent[0].kind == EnvelopeKind.ACTION
    assert sent[0].payload == "actions:list"


class _DummyWS:
    async def send(self, _msg) -> None:  # pragma: no cover - not used in this test
        return None


@pytest.mark.asyncio
async def test_websocket_requires_explicit_kind() -> None:
    ws = WebSocketClientChannel(_DummyWS())

    async def sender(_msg: TransportEnvelope) -> None:
        return None

    ws.attach_agent_envelope_sender(sender)

    with pytest.raises(ValueError, match="kind"):
        await ws.handle_ws_message({"id": "req-1", "payload": "hello"})


@pytest.mark.asyncio
async def test_direct_client_channel_poll_receives_unmatched_agent_messages() -> None:
    channel = DirectClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        _ = msg

    channel.attach_agent_envelope_sender(sender)
    receiver = channel.agent_envelope_receiver()

    await receiver(
        TransportEnvelope(
            id="event-1",
            kind=EnvelopeKind.MESSAGE,
            payload={"type": "approval_pending", "request_id": "req-1"},
        )
    )

    polled = await channel.poll(timeout=0.2)
    assert polled is not None
    assert polled.id == "event-1"
    assert isinstance(polled.payload, dict)
    assert polled.payload.get("type") == "approval_pending"


@pytest.mark.asyncio
async def test_direct_client_channel_poll_times_out_when_empty() -> None:
    channel = DirectClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        _ = msg

    channel.attach_agent_envelope_sender(sender)
    polled = await channel.poll(timeout=0.05)
    assert polled is None
