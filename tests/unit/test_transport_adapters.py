from __future__ import annotations

import asyncio
import json

import pytest

from dare_framework.transport import PollableClientChannel
from dare_framework.transport._internal.adapters import DirectClientChannel, StdioClientChannel, WebSocketClientChannel
from dare_framework.transport.types import (
    ActionPayload,
    EnvelopeKind,
    MessageKind,
    MessagePayload,
    SelectDomain,
    SelectKind,
    SelectPayload,
    TransportEnvelope,
)


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
    assert sent[0].kind is EnvelopeKind.ACTION
    assert isinstance(sent[0].payload, ActionPayload)
    assert sent[0].payload.resource_action == "actions:list"


@pytest.mark.asyncio
async def test_stdio_slash_command_extracts_action_params(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[TransportEnvelope] = []
    stdio = StdioClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        sent.append(msg)

    stdio.attach_agent_envelope_sender(sender)
    lines = iter(["/approvals grant req-1 scope=workspace matcher=exact_params session_id=session-42", "/quit"])

    async def fake_to_thread(_fn, _prompt):
        return next(lines)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    await stdio.start()

    envelope = sent[0]
    assert envelope.kind is EnvelopeKind.ACTION
    assert isinstance(envelope.payload, ActionPayload)
    assert envelope.payload.resource_action == "approvals:grant"
    assert envelope.payload.params == {
        "request_id": "req-1",
        "scope": "workspace",
        "matcher": "exact_params",
        "session_id": "session-42",
    }


class _DummyWS:
    async def send(self, _msg) -> None:  # pragma: no cover
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
async def test_websocket_serializer_uses_typed_payload_without_event_type() -> None:
    ws = _CaptureWS()
    channel = WebSocketClientChannel(ws)
    receiver = channel.agent_envelope_receiver()
    await receiver(
        TransportEnvelope(
            id="evt-1",
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id="msg-1",
                role="assistant",
                message_kind=MessageKind.CHAT,
                text="hello",
                data={"success": True, "output": "hello"},
            ),
        )
    )

    data = json.loads(ws.sent[0])
    assert data["kind"] == EnvelopeKind.MESSAGE.value
    assert "event_type" not in data
    assert data["payload"]["message_kind"] == MessageKind.CHAT.value


@pytest.mark.asyncio
async def test_websocket_deserializer_builds_typed_message_payload() -> None:
    ws = WebSocketClientChannel(_DummyWS())
    received: list[TransportEnvelope] = []

    async def sender(msg: TransportEnvelope) -> None:
        received.append(msg)

    ws.attach_agent_envelope_sender(sender)
    await ws.handle_ws_message(
        {
            "id": "req-1",
            "kind": "message",
            "payload": {
                "id": "msg-1",
                "role": "user",
                "message_kind": "chat",
                "text": "hello",
                "attachments": [{"kind": "image", "uri": "https://example.com/a.png"}],
            },
        }
    )

    assert len(received) == 1
    assert isinstance(received[0].payload, MessagePayload)
    assert received[0].payload.attachments[0].uri == "https://example.com/a.png"


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
            kind=EnvelopeKind.SELECT,
            payload=SelectPayload(
                id="approval-1",
                select_kind=SelectKind.ASK,
                select_domain=SelectDomain.APPROVAL,
                prompt="approve?",
                options=[{"label": "allow"}, {"label": "deny"}],
            ),
        )
    )

    polled = await channel.poll(timeout=0.2)
    assert polled is not None
    assert polled.kind is EnvelopeKind.SELECT
    assert isinstance(polled.payload, SelectPayload)
    assert polled.payload.select_kind is SelectKind.ASK


@pytest.mark.asyncio
async def test_direct_client_channel_poll_times_out_when_empty() -> None:
    channel = DirectClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        _ = msg

    channel.attach_agent_envelope_sender(sender)
    assert await channel.poll(timeout=0.05) is None


def test_direct_client_channel_matches_pollable_protocol() -> None:
    channel = DirectClientChannel()
    assert isinstance(channel, PollableClientChannel)


@pytest.mark.asyncio
async def test_stdio_receiver_renders_select_payload(capsys) -> None:
    channel = StdioClientChannel()
    receiver = channel.agent_envelope_receiver()
    await receiver(
        TransportEnvelope(
            id="evt-select",
            kind=EnvelopeKind.SELECT,
            payload=SelectPayload(
                id="req-42",
                select_kind=SelectKind.ASK,
                select_domain=SelectDomain.APPROVAL,
                prompt="approve?",
            ),
        )
    )

    captured = capsys.readouterr()
    assert "approval pending: request_id=req-42" in captured.out


@pytest.mark.asyncio
async def test_stdio_receiver_renders_message_payload_text(capsys) -> None:
    channel = StdioClientChannel()
    receiver = channel.agent_envelope_receiver()
    await receiver(
        TransportEnvelope(
            id="evt-thinking",
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id="msg-thinking",
                role="assistant",
                message_kind=MessageKind.THINKING,
                text="need tool data",
            ),
        )
    )

    captured = capsys.readouterr()
    assert "Assistant: need tool data" in captured.out
