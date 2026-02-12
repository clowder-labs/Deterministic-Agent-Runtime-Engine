from __future__ import annotations

from typing import Any

import pytest

from dare_framework.hook._internal.agent_event_transport_hook import AgentEventTransportHook
from dare_framework.hook.types import HookPhase
from dare_framework.transport import TransportEventType


class _RecordingTransport:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send(self, msg: Any) -> None:
        self.sent.append(msg)


@pytest.mark.asyncio
async def test_agent_event_transport_hook_sets_event_type() -> None:
    transport = _RecordingTransport()
    hook = AgentEventTransportHook(transport)

    await hook.invoke(HookPhase.BEFORE_PLAN, payload={"task_id": "task-1"})

    assert len(transport.sent) == 1
    envelope = transport.sent[0]
    assert envelope.event_type == TransportEventType.HOOK.value
    assert isinstance(envelope.payload, dict)
    assert envelope.payload.get("phase") == HookPhase.BEFORE_PLAN.value
