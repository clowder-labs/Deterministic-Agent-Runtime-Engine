"""Minimal client channel adapters for transport."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from dare_framework.transport.kernel import ClientChannel
from dare_framework.transport.types import Receiver, Sender, TransportEnvelope, new_envelope_id


class StdioClientChannel(ClientChannel):
    """Minimal stdio adapter for local interactive sessions."""

    def __init__(
        self,
        *,
        prompt: str = "You: ",
        quit_commands: tuple[str, ...] = ("/quit", "/exit"),
    ) -> None:
        self._prompt = prompt
        self._quit_commands = quit_commands
        self._sender: Sender | None = None
        self._stopped = False

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            payload = msg.payload
            if isinstance(payload, dict) and "output" in payload:
                output = payload.get("output")
            else:
                output = payload
            print(f"\nAssistant: {output}\n", flush=True)

        return recv

    async def start(self) -> None:
        if self._sender is None:
            raise RuntimeError("Sender not attached")
        while not self._stopped:
            line = await asyncio.to_thread(input, self._prompt)
            if line is None:
                continue
            line = line.strip()
            if not line:
                continue
            if line in self._quit_commands:
                await self._sender(
                    TransportEnvelope(
                        id=new_envelope_id(),
                        kind="control",
                        type="stop",
                    )
                )
                break
            await self._sender(
                TransportEnvelope(
                    id=new_envelope_id(),
                    type="prompt",
                    payload=line,
                )
            )

    async def stop(self) -> None:
        self._stopped = True


class WebSocketClientChannel(ClientChannel):
    """Minimal websocket adapter (expects an object with an async send method)."""

    def __init__(
        self,
        ws: Any,
        *,
        serializer: Callable[[TransportEnvelope], Any] | None = None,
        deserializer: Callable[[Any], TransportEnvelope] | None = None,
    ) -> None:
        self._ws = ws
        self._serializer = serializer or _default_serialize
        self._deserializer = deserializer or _default_deserialize
        self._sender: Sender | None = None

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            await self._ws.send(self._serializer(msg))

        return recv

    async def handle_ws_message(self, raw: Any) -> None:
        if self._sender is None:
            raise RuntimeError("Sender not attached")
        envelope = self._deserializer(raw)
        await self._sender(envelope)


class DirectClientChannel(ClientChannel):
    """Direct in-process adapter for request/response patterns."""

    def __init__(self) -> None:
        self._sender: Sender | None = None
        self._pending: dict[str, asyncio.Future[TransportEnvelope]] = {}

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            if msg.reply_to and msg.reply_to in self._pending:
                fut = self._pending[msg.reply_to]
                if not fut.done():
                    fut.set_result(msg)

        return recv

    async def ask(self, req: TransportEnvelope, timeout: float = 30.0) -> TransportEnvelope:
        if self._sender is None:
            raise RuntimeError("Sender not attached")
        if not req.id:
            req = TransportEnvelope(
                id=new_envelope_id(),
                reply_to=req.reply_to,
                kind=req.kind,
                type=req.type,
                payload=req.payload,
                meta=req.meta,
                stream_id=req.stream_id,
                seq=req.seq,
            )
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[req.id] = fut
        try:
            await self._sender(req)
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(req.id, None)


def _default_serialize(msg: TransportEnvelope) -> str:
    data = {
        "id": msg.id,
        "reply_to": msg.reply_to,
        "kind": msg.kind,
        "type": msg.type,
        "payload": msg.payload,
        "meta": msg.meta,
        "stream_id": msg.stream_id,
        "seq": msg.seq,
    }
    return json.dumps(data, ensure_ascii=False)


def _default_deserialize(raw: Any) -> TransportEnvelope:
    if isinstance(raw, str):
        data = json.loads(raw)
    elif isinstance(raw, dict):
        data = raw
    else:
        data = {"payload": raw}
    return TransportEnvelope(
        id=str(data.get("id") or new_envelope_id()),
        reply_to=data.get("reply_to"),
        kind=data.get("kind") or "data",
        type=data.get("type") or "message",
        payload=data.get("payload"),
        meta=data.get("meta") or {},
        stream_id=data.get("stream_id"),
        seq=data.get("seq"),
    )


__all__ = ["StdioClientChannel", "WebSocketClientChannel", "DirectClientChannel"]
