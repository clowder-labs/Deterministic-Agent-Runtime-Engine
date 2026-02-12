from __future__ import annotations

import pytest

from dare_framework.transport import normalize_transport_event_type
from dare_framework.transport.types import EnvelopeKind, TransportEnvelope, TransportEventType


def test_transport_envelope_does_not_derive_event_type_from_payload_type() -> None:
    envelope = TransportEnvelope(
        id="evt-no-derive",
        kind=EnvelopeKind.MESSAGE,
        payload={"type": "result"},
    )
    assert envelope.event_type is None


def test_transport_envelope_normalizes_legacy_event_type() -> None:
    envelope = TransportEnvelope(
        id="evt-legacy",
        kind="message",
        event_type="approval_pending",
        payload={"type": "approval_pending"},
    )
    assert envelope.kind == EnvelopeKind.MESSAGE
    assert envelope.event_type == TransportEventType.APPROVAL_PENDING.value


def test_transport_envelope_rejects_empty_event_type() -> None:
    with pytest.raises(ValueError, match="event_type must not be empty"):
        TransportEnvelope(
            id="evt-empty",
            kind=EnvelopeKind.MESSAGE,
            event_type="   ",
            payload={"type": "result"},
        )


def test_transport_facade_re_exports_event_type_normalizer() -> None:
    assert normalize_transport_event_type("approval_pending") == TransportEventType.APPROVAL_PENDING.value
