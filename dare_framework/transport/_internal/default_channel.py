"""Default transport channel implementation."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
from typing import TYPE_CHECKING

from dare_framework.transport.interaction.controls import AgentControl
from dare_framework.transport.kernel import AgentChannel, ClientChannel
from dare_framework.transport.types import (
    ActionPayload,
    ControlPayload,
    EnvelopeKind,
    MessagePayload,
    Receiver,
    Sender,
    TransportEnvelope,
    new_envelope_id,
)

if TYPE_CHECKING:
    from dare_framework.transport.interaction.control_handler import AgentControlHandler
    from dare_framework.transport.interaction.dispatcher import ActionDispatchResult, ActionHandlerDispatcher

_logger = logging.getLogger("dare.transport")


class DefaultAgentChannel(AgentChannel):
    """Queue-based AgentChannel with blocking backpressure and pump delivery."""

    def __init__(
        self,
        client_channel: ClientChannel,
        *,
        max_inbox: int,
        max_outbox: int,
        action_timeout_seconds: float = 30.0,
    ) -> None:
        self._client = client_channel
        self._receiver: Receiver = client_channel.agent_envelope_receiver()

        self._inbox: asyncio.Queue[TransportEnvelope] = asyncio.Queue(maxsize=max_inbox)
        self._outbox: asyncio.Queue[TransportEnvelope] = asyncio.Queue(maxsize=max_outbox)
        self._action_timeout_seconds = action_timeout_seconds if action_timeout_seconds > 0 else 30.0

        self._started = False
        self._out_pump_task: asyncio.Task[None] | None = None
        self._action_dispatcher: ActionHandlerDispatcher | None = None
        self._control_handler: AgentControlHandler | None = None

        async def sender(msg: TransportEnvelope) -> None:
            try:
                await self._enqueue_inbox(msg)
            except Exception:
                _logger.exception("agent channel sender failed")

        client_channel.attach_agent_envelope_sender(sender)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._out_pump_task = asyncio.create_task(self._pump_outbox_to_receiver())

    async def stop(self) -> None:
        if self._out_pump_task is not None:
            self._out_pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._out_pump_task
        self._out_pump_task = None
        self._started = False
        self._drain_outbox()

    async def poll(self) -> TransportEnvelope | list[TransportEnvelope]:
        return await self._inbox.get()

    async def send(self, msg: TransportEnvelope) -> None:
        # Direct-call agent flows may emit hook events before channel.start().
        # Drop these envelopes instead of blocking on the bounded outbox.
        if not self._started:
            _logger.warning(
                "agent channel not started; dropping outgoing envelope id=%s kind=%s",
                msg.id,
                msg.kind.value,
            )
            return
        await self._outbox.put(msg)

    def add_action_handler_dispatcher(self, dispatcher: ActionHandlerDispatcher) -> None:
        self._action_dispatcher = dispatcher

    def add_agent_control_handler(self, handler: AgentControlHandler) -> None:
        self._control_handler = handler

    def get_action_handler_dispatcher(self) -> ActionHandlerDispatcher | None:
        return self._action_dispatcher

    def get_agent_control_handler(self) -> AgentControlHandler | None:
        return self._control_handler

    async def _pump_outbox_to_receiver(self) -> None:
        while True:
            msg = await self._outbox.get()
            try:
                await self._receiver(msg)
            except Exception:
                _logger.exception("agent channel receiver failed")

    async def _enqueue_inbox(self, msg: TransportEnvelope) -> None:
        if msg.kind == EnvelopeKind.MESSAGE:
            if not isinstance(msg.payload, MessagePayload):
                await self._send_error(
                    reply_to=msg.id,
                    kind="message",
                    target="prompt",
                    code="INVALID_MESSAGE_PAYLOAD",
                    reason="invalid message payload (expected MessagePayload)",
                )
                return
            await self._inbox.put(msg)
            return

        if msg.kind == EnvelopeKind.ACTION:
            if self._action_dispatcher is None:
                await self._send_error(
                    reply_to=msg.id,
                    kind="action",
                    target=_action_target(msg.payload),
                    code="DISPATCHER_NOT_CONFIGURED",
                    reason="action dispatcher not configured",
                )
                return
            try:
                result = await asyncio.wait_for(
                    self._action_dispatcher.handle_action(msg),
                    timeout=self._action_timeout_seconds,
                )
            except asyncio.TimeoutError:
                await self._send_error(
                    reply_to=msg.id,
                    kind="action",
                    target=_action_target(msg.payload),
                    code="ACTION_TIMEOUT",
                    reason=f"action exceeded timeout ({self._action_timeout_seconds:.2f}s)",
                )
            except Exception as exc:
                await self._send_error(
                    reply_to=msg.id,
                    kind="action",
                    target=_action_target(msg.payload),
                    code="ACTION_DISPATCH_FAILED",
                    reason=f"action dispatch failed: {exc}",
                )
            else:
                await self._write_action_result(reply_to=msg.id, result=result)
            return

        if msg.kind == EnvelopeKind.CONTROL:
            await self._handle_control(msg)
            return

        await self._send_error(
            reply_to=msg.id,
            kind="message",
            target="envelope",
            code="UNSUPPORTED_ENVELOPE_KIND",
            reason=f"unsupported envelope kind: {msg.kind!r}",
        )

    def _drain_outbox(self) -> None:
        while not self._outbox.empty():
            with contextlib.suppress(asyncio.QueueEmpty):
                self._outbox.get_nowait()

    async def _handle_control(self, msg: TransportEnvelope) -> None:
        if self._control_handler is None:
            await self._send_error(
                reply_to=msg.id,
                kind="control",
                target="control",
                code="CONTROL_HANDLER_NOT_CONFIGURED",
                reason="control handler not configured",
            )
            return

        payload = msg.payload
        if not isinstance(payload, ControlPayload):
            await self._send_error(
                reply_to=msg.id,
                kind="control",
                target="control",
                code="INVALID_CONTROL_PAYLOAD",
                reason="invalid control payload (expected ControlPayload)",
            )
            return
        if not isinstance(payload.params, dict):
            await self._send_error(
                reply_to=msg.id,
                kind="control",
                target=payload.control_id or "control",
                code="INVALID_CONTROL_PAYLOAD",
                reason="invalid control payload (expected params mapping)",
            )
            return

        params: dict[str, object] = {}
        # Normalize kwargs eagerly so malformed key types return a structured
        # protocol error instead of being dropped by an uncaught TypeError.
        for raw_key, value in payload.params.items():
            if not isinstance(raw_key, str):
                await self._send_error(
                    reply_to=msg.id,
                    kind="control",
                    target=payload.control_id or "control",
                    code="INVALID_CONTROL_PAYLOAD",
                    reason="invalid control payload (expected string param keys)",
                )
                return
            params[raw_key] = value

        if not isinstance(msg.meta, dict):
            await self._send_error(
                reply_to=msg.id,
                kind="control",
                target=payload.control_id or "control",
                code="INVALID_CONTROL_PAYLOAD",
                reason="invalid control payload (expected metadata mapping)",
            )
            return

        # Normalize metadata keys eagerly so malformed key types return a
        # structured protocol error instead of being dropped by TypeError.
        for raw_key, value in msg.meta.items():
            if not isinstance(raw_key, str):
                await self._send_error(
                    reply_to=msg.id,
                    kind="control",
                    target=payload.control_id or "control",
                    code="INVALID_CONTROL_PAYLOAD",
                    reason="invalid control payload (expected string metadata keys)",
                )
                return
            params[raw_key] = value

        control = AgentControl.value_of(payload.control_id)
        if control is None:
            await self._send_error(
                reply_to=msg.id,
                kind="control",
                target=payload.control_id or "control",
                code="UNSUPPORTED_OPERATION",
                reason=f"unknown control: {payload.control_id!r}",
            )
            return

        try:
            result = self._control_handler.invoke(control, **params)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            await self._send_error(
                reply_to=msg.id,
                kind="control",
                target=control.value,
                code="CONTROL_HANDLER_FAILED",
                reason=f"control handler failed: {exc}",
            )
            return

        if result is not None:
            await self._send_result(
                reply_to=msg.id,
                kind="control",
                target=control.value,
                resp=result,
            )

    async def _write_action_result(self, *, reply_to: str | None, result: ActionDispatchResult) -> None:
        if result.ok:
            await self._send_result(
                reply_to=reply_to,
                kind="action",
                target=result.target,
                resp=result.resp,
            )
            return
        await self._send_error(
            reply_to=reply_to,
            kind="action",
            target=result.target,
            code=result.code or "ACTION_DISPATCH_FAILED",
            reason=result.reason or "action dispatch failed",
        )

    async def _send_result(
        self,
        *,
        reply_to: str | None,
        kind: str,
        target: str,
        resp: object,
    ) -> None:
        await self.send(
            _build_reply_envelope(
                reply_to=reply_to,
                kind=kind,
                target=target,
                ok=True,
                result=resp,
            )
        )

    async def _send_error(
        self,
        *,
        reply_to: str | None,
        kind: str,
        target: str,
        code: str,
        reason: str,
    ) -> None:
        await self.send(
            _build_reply_envelope(
                reply_to=reply_to,
                kind=kind,
                target=target,
                ok=False,
                code=code,
                reason=reason,
            )
        )

def _action_target(payload: object) -> str:
    if isinstance(payload, ActionPayload) and payload.resource_action.strip():
        return payload.resource_action.strip()
    return "action"


def _build_reply_envelope(
    *,
    reply_to: str | None,
    kind: str,
    target: str,
    ok: bool,
    result: object | None = None,
    code: str | None = None,
    reason: str | None = None,
) -> TransportEnvelope:
    if kind == "message":
        text = ""
        data: dict[str, object] = {
            "success": ok,
            "target": target,
        }
        if ok:
            if isinstance(result, dict):
                text = str(result.get("output") or "")
                data["result"] = result
            else:
                text = str(result or "")
                data["result"] = result
            message_kind = "chat"
        else:
            text = reason or code or "transport error"
            if code is not None:
                data["code"] = code
            if reason is not None:
                data["reason"] = reason
            message_kind = "summary"
        return TransportEnvelope(
            id=new_envelope_id(),
            reply_to=reply_to,
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id=new_envelope_id(),
                role="assistant",
                message_kind=message_kind,
                text=text,
                data=data,
            ),
        )
    if kind == "action":
        return TransportEnvelope(
            id=new_envelope_id(),
            reply_to=reply_to,
            kind=EnvelopeKind.ACTION,
            payload=ActionPayload(
                id=new_envelope_id(),
                resource_action=target,
                ok=ok,
                result=result,
                code=code,
                reason=reason,
            ),
        )
    if kind == "control":
        return TransportEnvelope(
            id=new_envelope_id(),
            reply_to=reply_to,
            kind=EnvelopeKind.CONTROL,
            payload=ControlPayload(
                id=new_envelope_id(),
                control_id=target,
                ok=ok,
                result=result,
                code=code,
                reason=reason,
            ),
        )
    raise ValueError(f"unsupported reply kind: {kind!r}")
