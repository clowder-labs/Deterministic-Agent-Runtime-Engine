from __future__ import annotations

import pytest

from dare_framework.context.types import AttachmentKind
from dare_framework.transport.types import (
    ActionPayload,
    EnvelopeKind,
    MessageKind,
    MessagePayload,
    SelectDomain,
    SelectKind,
    SelectPayload,
    TransportEnvelope,
)


def test_transport_envelope_accepts_matching_typed_payload_family() -> None:
    envelope = TransportEnvelope(
        id="evt-message",
        kind=EnvelopeKind.MESSAGE,
        payload=MessagePayload(
            id="msg-1",
            role="assistant",
            message_kind=MessageKind.THINKING,
            text="need tool data",
        ),
    )

    assert envelope.kind is EnvelopeKind.MESSAGE
    assert envelope.payload.message_kind is MessageKind.THINKING


def test_transport_envelope_accepts_select_payload_with_strong_enums() -> None:
    envelope = TransportEnvelope(
        id="evt-select",
        kind=EnvelopeKind.SELECT,
        payload=SelectPayload(
            id="sel-1",
            select_kind=SelectKind.ASK,
            select_domain=SelectDomain.APPROVAL,
            prompt="approve?",
        ),
    )

    assert envelope.payload.select_kind is SelectKind.ASK
    assert envelope.payload.select_domain is SelectDomain.APPROVAL


def test_transport_envelope_rejects_mismatched_typed_payload_family() -> None:
    with pytest.raises(TypeError, match="invalid payload type for envelope kind"):
        TransportEnvelope(
            id="evt-mismatch",
            kind=EnvelopeKind.MESSAGE,
            payload=ActionPayload(
                id="act-1",
                resource_action="tools:list",
            ),
        )


def test_message_payload_rejects_attachments_for_thinking_kind() -> None:
    with pytest.raises(ValueError, match="attachments are not supported"):
        MessagePayload(
            id="msg-thinking-attachments",
            role="assistant",
            message_kind=MessageKind.THINKING,
            text="hidden reasoning",
            attachments=[{"kind": AttachmentKind.IMAGE, "uri": "https://example.com/a.png"}],
        )


def test_message_payload_rejects_non_dict_data() -> None:
    with pytest.raises(TypeError, match="invalid data type"):
        MessagePayload(
            id="msg-bad-data",
            role="assistant",
            message_kind=MessageKind.TOOL_CALL,
            text="call tool",
            data="not-a-dict",
        )


def test_transport_envelope_rejects_raw_message_payload() -> None:
    with pytest.raises(TypeError, match="expected MessagePayload"):
        TransportEnvelope(
            id="evt-raw",
            kind=EnvelopeKind.MESSAGE,
            payload="hello",
        )
