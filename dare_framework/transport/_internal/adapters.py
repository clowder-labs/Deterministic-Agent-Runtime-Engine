"""Minimal client channel adapters for transport."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from dare_framework.transport.interaction.controls import AgentControl
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.kernel import ClientChannel, PollableClientChannel
from dare_framework.transport.types import (
    canonicalize_transport_event_type,
    EnvelopeKind,
    Receiver,
    Sender,
    TransportEnvelope,
    TransportEventType,
    new_envelope_id,
)


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
            event_type = _resolve_transport_event_type(msg)
            payload = msg.payload
            if isinstance(payload, dict):
                if event_type == TransportEventType.MESSAGE.value:
                    kind = payload.get("kind")
                    resp = payload.get("resp")
                    if kind == "message":
                        if isinstance(resp, dict) and "output" in resp:
                            output = resp.get("output")
                        else:
                            output = payload.get("output")
                    else:
                        output = resp if resp is not None else payload
                elif event_type == TransportEventType.ERROR.value:
                    output = payload.get("reason") or payload.get("error")
                elif event_type == TransportEventType.THINKING.value:
                    resp = payload.get("resp")
                    if isinstance(resp, dict):
                        output = resp.get("output") or resp.get("thinking") or resp
                    else:
                        output = resp if resp is not None else payload
                elif event_type == TransportEventType.STATUS.value:
                    output = _render_status_output(payload)
                else:
                    output = payload
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
                # Quit is a client/host lifecycle operation. Do not send it as a transport control message.
                self._stopped = True
                return
            kind = EnvelopeKind.MESSAGE
            payload: Any = line
            meta: dict[str, Any] = {}
            if line.startswith("/"):
                token = line.lstrip("/").strip()
                if not token:
                    payload = ResourceAction.ACTIONS_LIST.value
                    kind = EnvelopeKind.ACTION
                else:
                    control = AgentControl.value_of(token)
                    if control is not None:
                        kind = EnvelopeKind.CONTROL
                        payload = control.value
                    else:
                        payload, meta = _normalize_slash_action(token)
                        kind = EnvelopeKind.ACTION
            await self._sender(
                TransportEnvelope(
                    id=new_envelope_id(),
                    kind=kind,
                    payload=payload,
                    meta=meta,
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


class DirectClientChannel(PollableClientChannel):
    """Direct in-process adapter for request/response patterns."""

    def __init__(self) -> None:
        self._sender: Sender | None = None
        self._pending: dict[str, asyncio.Future[TransportEnvelope]] = {}
        self._events: asyncio.Queue[TransportEnvelope] = asyncio.Queue()

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            if msg.reply_to and msg.reply_to in self._pending:
                fut = self._pending[msg.reply_to]
                if not fut.done():
                    fut.set_result(msg)
                    return
            await self._events.put(msg)

        return recv

    async def ask(self, req: TransportEnvelope, timeout: float = 30.0) -> TransportEnvelope:
        if self._sender is None:
            raise RuntimeError("Sender not attached")
        if not req.id:
            req = TransportEnvelope(
                id=new_envelope_id(),
                reply_to=req.reply_to,
                kind=req.kind,
                event_type=req.event_type,
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

    async def poll(self, timeout: float | None = None) -> TransportEnvelope | None:
        """Poll unsolicited envelopes emitted by the agent channel."""
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be >= 0")
        if timeout is None:
            return await self._events.get()
        try:
            return await asyncio.wait_for(self._events.get(), timeout)
        except asyncio.TimeoutError:
            return None


def _normalize_slash_action(token: str) -> tuple[str, dict[str, Any]]:
    # Canonical `resource:action` string is accepted as-is.
    direct = ResourceAction.value_of(token)
    if direct is not None:
        return direct.value, {}

    # Support CLI-style `/resource action ...` and map it to canonical action id.
    parts = token.split()
    if len(parts) >= 2:
        candidate = f"{parts[0]}:{parts[1]}"
        action = ResourceAction.value_of(candidate)
        if action is not None:
            return action.value, _extract_action_params(action, parts[2:])

    # Unknown slash command: preserve previous behavior for compatibility.
    return token, {}


def _extract_action_params(action: ResourceAction, tokens: list[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    positional: list[str] = []
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                params[key] = value
            continue
        positional.append(token)

    if action in {ResourceAction.APPROVALS_GRANT, ResourceAction.APPROVALS_DENY}:
        if positional:
            params.setdefault("request_id", positional[0])
    elif action == ResourceAction.APPROVALS_REVOKE:
        if positional:
            params.setdefault("rule_id", positional[0])
    elif action in {ResourceAction.MCP_LIST, ResourceAction.MCP_RELOAD}:
        if positional:
            params.setdefault("mcp_name", positional[0])
    elif action == ResourceAction.MCP_SHOW_TOOL:
        if positional:
            params.setdefault("mcp_name", positional[0])
        if len(positional) > 1:
            params.setdefault("tool_name", positional[1])

    return params


def _default_serialize(msg: TransportEnvelope) -> str:
    data = {
        "id": msg.id,
        "reply_to": msg.reply_to,
        "kind": msg.kind,
        "event_type": msg.event_type,
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
        raise ValueError("websocket envelope must be a JSON object with explicit kind")
    if not isinstance(data, dict):
        raise ValueError("websocket envelope must be a JSON object with explicit kind")
    if "kind" not in data or data.get("kind") in (None, ""):
        raise ValueError("websocket envelope requires explicit kind")
    return TransportEnvelope(
        id=str(data.get("id") or new_envelope_id()),
        reply_to=data.get("reply_to"),
        kind=data.get("kind"),
        event_type=data.get("event_type"),
        payload=data.get("payload"),
        meta=data.get("meta") or {},
        stream_id=data.get("stream_id"),
        seq=data.get("seq"),
    )


def _resolve_transport_event_type(msg: TransportEnvelope) -> str | None:
    """Resolve event_type for receiver routing."""
    if isinstance(msg.event_type, str):
        return canonicalize_transport_event_type(msg.event_type)
    return None


def _render_status_output(payload: dict[str, Any]) -> Any:
    """Render canonical status payload into a concise stdio output."""
    resp = payload.get("resp")
    if isinstance(resp, dict):
        if "phase" in resp:
            return resp.get("phase")
        request_id = resp.get("request_id")
        decision = resp.get("decision")
        if isinstance(resp.get("request"), dict):
            request_id = resp["request"].get("request_id")
        if request_id and decision is not None:
            return f"approval resolved: request_id={request_id} decision={decision}"
        if request_id:
            return f"approval pending: request_id={request_id}"
        if any(key in resp for key in ("request", "request_id", "decision")):
            return "approval update"
        if "phase" in resp:
            return resp.get("phase")
        if "event" in resp:
            return resp.get("event")
        return resp

    if "phase" in payload:
        return payload.get("phase")
    if "event" in payload:
        return payload.get("event")
    return payload


__all__ = ["StdioClientChannel", "WebSocketClientChannel", "DirectClientChannel"]
