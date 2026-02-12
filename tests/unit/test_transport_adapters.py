import asyncio
import json

import pytest

from dare_framework.transport import PollableClientChannel
from dare_framework.transport._internal.adapters import DirectClientChannel, StdioClientChannel, WebSocketClientChannel
from dare_framework.transport.types import EnvelopeKind, TransportEnvelope, TransportEventType


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


class _CaptureWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


@pytest.mark.asyncio
async def test_websocket_requires_explicit_kind() -> None:
    ws = WebSocketClientChannel(_DummyWS())

    async def sender(_msg: TransportEnvelope) -> None:
        return None

    ws.attach_agent_envelope_sender(sender)

    with pytest.raises(ValueError, match="kind"):
        await ws.handle_ws_message({"id": "req-1", "payload": "hello"})


@pytest.mark.asyncio
async def test_websocket_serializer_includes_event_type() -> None:
    ws = _CaptureWS()
    channel = WebSocketClientChannel(ws)
    receiver = channel.agent_envelope_receiver()
    await receiver(
        TransportEnvelope(
            id="evt-1",
            kind=EnvelopeKind.MESSAGE,
            event_type=TransportEventType.RESULT.value,
            payload={"ok": True},
        )
    )
    assert ws.sent
    data = json.loads(ws.sent[0])
    assert data["event_type"] == TransportEventType.RESULT.value


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
            event_type=TransportEventType.APPROVAL_PENDING.value,
            payload={"request_id": "req-1"},
        )
    )

    polled = await channel.poll(timeout=0.2)
    assert polled is not None
    assert polled.id == "event-1"
    assert polled.event_type == TransportEventType.APPROVAL_PENDING.value


@pytest.mark.asyncio
async def test_direct_client_channel_poll_times_out_when_empty() -> None:
    channel = DirectClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        _ = msg

    channel.attach_agent_envelope_sender(sender)
    polled = await channel.poll(timeout=0.05)
    assert polled is None


def test_direct_client_channel_matches_pollable_protocol() -> None:
    channel = DirectClientChannel()
    assert isinstance(channel, PollableClientChannel)


@pytest.mark.asyncio
async def test_stdio_receiver_uses_event_type_without_legacy_payload_type(capsys) -> None:
    channel = StdioClientChannel()
    receiver = channel.agent_envelope_receiver()
    await receiver(
        TransportEnvelope(
            id="evt-2",
            kind=EnvelopeKind.MESSAGE,
            event_type=TransportEventType.APPROVAL_PENDING.value,
            payload={"resp": {"request": {"request_id": "req-42"}}},
        )
    )
    captured = capsys.readouterr()
    assert "approval pending: request_id=req-42" in captured.out


@pytest.mark.asyncio
async def test_stdio_receiver_does_not_route_by_payload_type_without_event_type(capsys) -> None:
    channel = StdioClientChannel()
    receiver = channel.agent_envelope_receiver()

    await receiver(
        TransportEnvelope(
            id="evt-legacy-result",
            kind=EnvelopeKind.MESSAGE,
            payload={
                "type": "result",
                "kind": "message",
                "resp": {"output": "hello"},
            },
        )
    )

    captured = capsys.readouterr()
    assert "Assistant: {'type': 'result'" in captured.out
    assert "Assistant: hello" not in captured.out
