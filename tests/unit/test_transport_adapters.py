import asyncio

import pytest

from dare_framework.transport._internal.adapters import StdioClientChannel, WebSocketClientChannel
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
