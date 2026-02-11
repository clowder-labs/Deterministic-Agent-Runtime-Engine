"""Hook implementation that forwards agent events to a transport channel."""

from __future__ import annotations

import logging
from typing import Any, Literal

from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.transport.kernel import AgentChannel
from dare_framework.transport.types import TransportEnvelope, new_envelope_id

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
        # Avoid blocking direct-call flows when an AgentChannel is attached but not started.
        # DefaultAgentChannel uses bounded outbox + background pump; before start(), send() may block.
        if not _channel_started(self._transport):
            return None
        payload = kwargs.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            payload={
                "type": "hook",
                "phase": phase.value,
                "payload": payload,
            },
        )
        try:
            await self._transport.send(envelope)
        except Exception:
            _logger.exception("agent event transport hook send failed")
            return None
        return None


def _channel_started(transport: AgentChannel) -> bool:
    is_started = getattr(transport, "is_started", None)
    if callable(is_started):
        try:
            return bool(is_started())
        except Exception:
            return False
    started_flag = getattr(transport, "_started", None)
    if isinstance(started_flag, bool):
        return started_flag
    # Unknown transport implementation: preserve prior behavior.
    return True


__all__ = ["AgentEventTransportHook"]
