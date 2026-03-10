"""Minimal client channel adapters for transport."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from dare_framework.context.types import MessageKind, MessageRole
from dare_framework.transport.interaction.controls import AgentControl
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.kernel import ClientChannel, PollableClientChannel
from dare_framework.transport.serialization import jsonify_transport_value
from dare_framework.transport.types import (
    ActionPayload,
    ControlPayload,
    EnvelopeKind,
    MessagePayload,
    Receiver,
    Sender,
    SelectDomain,
    SelectKind,
    SelectPayload,
    TransportEnvelope,
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
            payload = msg.payload
            if isinstance(payload, SelectPayload):
                output = _render_select_output(payload)
            elif isinstance(payload, MessagePayload):
                output = _render_message_output(payload)
            elif isinstance(payload, ActionPayload):
                output = _render_action_output(payload)
            elif isinstance(payload, ControlPayload):
                output = _render_control_output(payload)
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
            payload: Any = MessagePayload(
                id=new_envelope_id(),
                role=MessageRole.USER,
                message_kind=MessageKind.CHAT,
                text=line,
            )
            meta: dict[str, Any] = {}
            if line.startswith("/"):
                token = line.lstrip("/").strip()
                if not token:
                    payload = ActionPayload(
                        id=new_envelope_id(),
                        resource_action=ResourceAction.ACTIONS_LIST.value,
                    )
                    kind = EnvelopeKind.ACTION
                else:
                    control = AgentControl.value_of(token)
                    if control is not None:
                        kind = EnvelopeKind.CONTROL
                        payload = ControlPayload(
                            id=new_envelope_id(),
                            control_id=control.value,
                        )
                    else:
                        resource_action, meta = _normalize_slash_action(token)
                        payload = ActionPayload(
                            id=new_envelope_id(),
                            resource_action=resource_action,
                            params=meta,
                        )
                        kind = EnvelopeKind.ACTION
                        meta = {}
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

    # Unknown slash command: keep it as an explicit action id so the transport
    # contract stays open for custom action handlers.
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
        "kind": msg.kind.value if isinstance(msg.kind, EnvelopeKind) else msg.kind,
        "payload": jsonify_transport_value(msg.payload),
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
        payload=_deserialize_payload(kind=data.get("kind"), payload=data.get("payload")),
        meta=data.get("meta") or {},
        stream_id=data.get("stream_id"),
        seq=data.get("seq"),
    )


def _render_select_output(payload: SelectPayload) -> str:
    """Render typed select payloads into concise stdio text."""
    if payload.select_domain == SelectDomain.APPROVAL:
        if payload.select_kind == SelectKind.ASK:
            request = payload.metadata.get("request")
            if isinstance(request, dict):
                request_id = request.get("request_id")
                if request_id:
                    return f"approval pending: request_id={request_id}"
            if payload.id:
                return f"approval pending: request_id={payload.id}"
            return "approval pending"
        if payload.select_kind == SelectKind.ANSWERED:
            selected = payload.selected
            if isinstance(selected, dict):
                request_id = selected.get("request_id") or payload.id
                decision = selected.get("decision")
                if request_id and decision is not None:
                    return f"approval resolved: request_id={request_id} decision={decision}"
            if payload.id:
                return f"approval resolved: request_id={payload.id}"
            return "approval resolved"
    if payload.prompt:
        return payload.prompt
    return payload.select_kind


def _render_message_output(payload: MessagePayload) -> Any:
    if payload.message_kind == MessageKind.THINKING:
        return payload.text or ""
    if isinstance(payload.data, dict):
        result = payload.data.get("result")
        if isinstance(result, dict):
            output = result.get("output")
            if output is not None and payload.text in (None, ""):
                return output
        reason = payload.data.get("reason")
        if payload.data.get("success") is False and reason:
            return reason
    return payload.text or ""


def _render_action_output(payload: ActionPayload) -> Any:
    if payload.ok is False:
        return payload.reason or payload.code or payload.resource_action
    if payload.result is not None:
        return payload.result
    return payload.resource_action


def _render_control_output(payload: ControlPayload) -> Any:
    if payload.ok is False:
        return payload.reason or payload.code or payload.control_id
    if payload.result is not None:
        return payload.result
    return payload.control_id


def _deserialize_payload(*, kind: Any, payload: Any) -> Any:
    if not isinstance(kind, str) or not isinstance(payload, dict):
        return payload
    try:
        envelope_kind = EnvelopeKind(kind)
    except ValueError:
        return payload
    if envelope_kind == EnvelopeKind.MESSAGE:
        return MessagePayload(
            id=str(payload.get("id") or new_envelope_id()),
            metadata=_dict(payload.get("metadata")),
            role=payload.get("role", MessageRole.USER),
            message_kind=payload.get("message_kind", MessageKind.CHAT),
            text=_opt_str(payload.get("text")),
            attachments=_list(payload.get("attachments")),
            data=_dict_or_none(payload.get("data")),
        )
    if envelope_kind == EnvelopeKind.SELECT:
        return SelectPayload(
            id=str(payload.get("id") or new_envelope_id()),
            metadata=_dict(payload.get("metadata")),
            select_kind=payload.get("select_kind", SelectKind.ASK),
            select_domain=payload.get("select_domain", SelectDomain.CHOICE),
            prompt=_opt_str(payload.get("prompt")),
            options=_list_of_dicts(payload.get("options")),
            selected=payload.get("selected"),
        )
    if envelope_kind == EnvelopeKind.ACTION:
        return ActionPayload(
            id=str(payload.get("id") or new_envelope_id()),
            metadata=_dict(payload.get("metadata")),
            resource_action=str(payload.get("resource_action") or ""),
            params=_dict(payload.get("params")),
            ok=_opt_bool(payload.get("ok")),
            result=payload.get("result"),
            code=_opt_str(payload.get("code")),
            reason=_opt_str(payload.get("reason")),
        )
    if envelope_kind == EnvelopeKind.CONTROL:
        return ControlPayload(
            id=str(payload.get("id") or new_envelope_id()),
            metadata=_dict(payload.get("metadata")),
            control_id=str(payload.get("control_id") or ""),
            params=_dict(payload.get("params")),
            ok=_opt_bool(payload.get("ok")),
            result=payload.get("result"),
            code=_opt_str(payload.get("code")),
            reason=_opt_str(payload.get("reason")),
        )
    return payload


def _dict(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items()}


def _dict_or_none(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    return _dict(raw)


def _list_of_dicts(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            items.append({str(key): value for key, value in item.items()})
    return items


def _list(raw: Any) -> list[Any]:
    if not isinstance(raw, list):
        return []
    return list(raw)


def _opt_str(raw: Any) -> str | None:
    if raw is None:
        return None
    return str(raw)


def _opt_bool(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    return None


__all__ = ["StdioClientChannel", "WebSocketClientChannel", "DirectClientChannel"]
