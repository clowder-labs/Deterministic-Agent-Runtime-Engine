"""Hook implementation that forwards agent events to a transport channel."""

from __future__ import annotations

import logging
from typing import Any, Literal

from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.transport.kernel import AgentChannel
from dare_framework.transport.types import EnvelopeKind, MessageKind, MessagePayload, MessageRole, TransportEnvelope, new_envelope_id

_logger = logging.getLogger("dare.hook")


class AgentEventTransportHook(IHook):
    """Emit hook events as transport messages."""

    def __init__(self, transport: AgentChannel) -> None:
        self._transport = transport

    @property
    def name(self) -> str:
        return "agent_event_transport"

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> Any:
        _ = args
        payload = kwargs.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id=new_envelope_id(),
                role=MessageRole.ASSISTANT,
                message_kind=MessageKind.SUMMARY,
                text=f"hook:{phase.value}",
                data={
                    "source": "hook",
                    "phase": phase.value,
                    "payload": payload,
                },
            ),
        )
        try:
            await self._transport.send(envelope)
        except Exception:
            _logger.exception("agent event transport hook send failed")
            return None
        return None


__all__ = ["AgentEventTransportHook"]
