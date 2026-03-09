from __future__ import annotations

from typing import Any

import pytest

from dare_framework.hook._internal.agent_event_transport_hook import AgentEventTransportHook
from dare_framework.hook.types import HookPhase
from dare_framework.transport import EnvelopeKind, MessageKind, MessagePayload, MessageRole


class _RecordingTransport:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send(self, msg: Any) -> None:
        self.sent.append(msg)


@pytest.mark.asyncio
async def test_agent_event_transport_hook_emits_typed_message_payload() -> None:
    transport = _RecordingTransport()
    hook = AgentEventTransportHook(transport)

    await hook.invoke(HookPhase.BEFORE_PLAN, payload={"task_id": "task-1"})

    assert len(transport.sent) == 1
    envelope = transport.sent[0]
    assert envelope.kind is EnvelopeKind.MESSAGE
    assert isinstance(envelope.payload, MessagePayload)
    assert envelope.payload.role is MessageRole.ASSISTANT
    assert envelope.payload.message_kind is MessageKind.SUMMARY
    assert envelope.payload.data == {
        "source": "hook",
        "phase": HookPhase.BEFORE_PLAN.value,
        "payload": {"task_id": "task-1"},
    }
