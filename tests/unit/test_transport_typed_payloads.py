from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from dare_framework.transport import (
    AgentChannel,
    DirectClientChannel,
    EnvelopeKind,
    TransportEnvelope,
    WebSocketClientChannel,
    new_envelope_id,
)
from dare_framework.transport.interaction.control_handler import AgentControlHandler
from dare_framework.transport.interaction.dispatcher import ActionHandlerDispatcher
from dare_framework.transport.interaction.handlers import IActionHandler
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.types import ActionPayload, ControlPayload, MessagePayload, SelectPayload
from dare_framework.transport.types import MessageKind, SelectDomain, SelectKind


class _DummyClientChannel:
    def __init__(self, receiver):
        self._receiver = receiver
        self.sender = None

    def attach_agent_envelope_sender(self, sender):
        self.sender = sender

    def agent_envelope_receiver(self):
        return self._receiver


class _FakeAgent:
    def __init__(self) -> None:
        self.interrupted = False

    def interrupt(self) -> dict[str, bool]:
        self.interrupted = True
        return {"ok": True}

    def pause(self):  # pragma: no cover
        return None

    def retry(self):  # pragma: no cover
        return None

    def reverse(self):  # pragma: no cover
        return None


class _RecordActionHandler(IActionHandler):
    def __init__(self, calls: list[tuple[str, dict[str, Any]]]) -> None:
        self._calls = calls

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.TOOLS_LIST}

    async def invoke(self, action: ResourceAction, **params: object):
        normalized = {str(key): value for key, value in params.items()}
        self._calls.append((action.value, normalized))
        return {"ok": True}


class _CaptureWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def test_transport_envelope_accepts_matching_typed_payload_families() -> None:
    message = TransportEnvelope(
        id="msg-env",
        kind=EnvelopeKind.MESSAGE,
        payload=MessagePayload(
            id="msg-1",
            role="user",
            message_kind="chat",
            text="hello",
        ),
    )
    select = TransportEnvelope(
        id="sel-env",
        kind=EnvelopeKind.SELECT,
        payload=SelectPayload(
            id="sel-1",
            select_kind="ask",
            select_domain="approval",
            prompt="approve?",
            options=[{"label": "allow"}, {"label": "deny"}],
        ),
    )
    action = TransportEnvelope(
        id="act-env",
        kind=EnvelopeKind.ACTION,
        payload=ActionPayload(
            id="act-1",
            resource_action=ResourceAction.TOOLS_LIST.value,
        ),
    )
    control = TransportEnvelope(
        id="ctl-env",
        kind=EnvelopeKind.CONTROL,
        payload=ControlPayload(
            id="ctl-1",
            control_id="interrupt",
        ),
    )

    assert isinstance(message.payload, MessagePayload)
    assert isinstance(select.payload, SelectPayload)
    assert isinstance(action.payload, ActionPayload)
    assert isinstance(control.payload, ControlPayload)
    assert message.payload.message_kind is MessageKind.CHAT
    assert select.payload.select_kind is SelectKind.ASK
    assert select.payload.select_domain is SelectDomain.APPROVAL


def test_transport_envelope_rejects_mismatched_typed_payload_family() -> None:
    with pytest.raises(TypeError, match="invalid payload type for envelope kind"):
        TransportEnvelope(
            id="bad-env",
            kind=EnvelopeKind.MESSAGE,
            payload=ActionPayload(
                id="act-1",
                resource_action=ResourceAction.TOOLS_LIST.value,
            ),
        )


@pytest.mark.asyncio
async def test_action_envelope_dispatches_using_action_payload() -> None:
    async def receiver(_msg: TransportEnvelope) -> None:
        return None

    client = _DummyClientChannel(receiver)
    channel = AgentChannel.build(client)
    calls: list[tuple[str, dict[str, Any]]] = []
    dispatcher = ActionHandlerDispatcher()
    dispatcher.register_action_handler(_RecordActionHandler(calls))
    channel.add_action_handler_dispatcher(dispatcher)

    sender = client.sender
    assert sender is not None
    await sender(
        TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.ACTION,
            payload=ActionPayload(
                id="act-1",
                resource_action=ResourceAction.TOOLS_LIST.value,
                params={"verbose": True},
            ),
        )
    )

    assert calls == [(ResourceAction.TOOLS_LIST.value, {"verbose": True})]


@pytest.mark.asyncio
async def test_control_envelope_dispatches_using_control_payload() -> None:
    async def receiver(_msg: TransportEnvelope) -> None:
        return None

    client = _DummyClientChannel(receiver)
    channel = AgentChannel.build(client)
    fake_agent = _FakeAgent()
    channel.add_agent_control_handler(AgentControlHandler(fake_agent))

    sender = client.sender
    assert sender is not None
    await sender(
        TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.CONTROL,
            payload=ControlPayload(
                id="ctl-1",
                control_id="interrupt",
            ),
        )
    )

    assert fake_agent.interrupted is True


@pytest.mark.asyncio
async def test_direct_client_channel_round_trips_select_payload() -> None:
    channel = DirectClientChannel()

    async def sender(msg: TransportEnvelope) -> None:
        receiver = channel.agent_envelope_receiver()
        await receiver(msg)

    channel.attach_agent_envelope_sender(sender)

    envelope = TransportEnvelope(
        id="select-event-1",
        kind=EnvelopeKind.SELECT,
        payload=SelectPayload(
            id="approval-1",
            select_kind="ask",
            select_domain="approval",
            prompt="approve?",
            options=[{"label": "allow"}, {"label": "deny"}],
        ),
    )

    receiver = channel.agent_envelope_receiver()
    await receiver(envelope)
    polled = await channel.poll(timeout=0.2)
    assert polled is not None
    assert polled.kind == EnvelopeKind.SELECT
    assert isinstance(polled.payload, SelectPayload)
    assert polled.payload.select_kind == "ask"


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
                message_kind="thinking",
                text="need tool data",
            ),
        )
    )

    assert ws.sent
    data = json.loads(ws.sent[0])
    assert "event_type" not in data or data["event_type"] is None
    assert data["kind"] == EnvelopeKind.MESSAGE.value
    assert data["payload"]["message_kind"] == "thinking"
