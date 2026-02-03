"""transport domain facade."""

from dare_framework.transport.interfaces import AgentChannel, ClientChannel
from dare_framework.transport.types import (
    EnvelopeKind,
    EnvelopeDecoder,
    EnvelopeEncoder,
    TransportEnvelope,
    new_envelope_id,
    Receiver,
    Sender,
)
from dare_framework.transport._internal import (
    DefaultAgentChannel,
    DirectClientChannel,
    StdioClientChannel,
    WebSocketClientChannel,
)

__all__ = [
    "AgentChannel",
    "ClientChannel",
    "EnvelopeKind",
    "EnvelopeDecoder",
    "EnvelopeEncoder",
    "TransportEnvelope",
    "new_envelope_id",
    "Receiver",
    "Sender",
    "DefaultAgentChannel",
    "DirectClientChannel",
    "StdioClientChannel",
    "WebSocketClientChannel",
]
