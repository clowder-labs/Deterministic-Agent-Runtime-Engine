"""transport domain facade."""

from dare_framework.transport.interfaces import AgentChannel, ClientChannel, PollableClientChannel
from dare_framework.transport.types import (
    canonicalize_transport_event_type,
    EnvelopeKind,
    TransportEventType,
    TransportEnvelope,
    normalize_transport_event_type,
    new_envelope_id,
    Receiver,
    Sender,
)
from dare_framework.transport.interaction import (
    AgentControl,
    ActionHandlerDispatcher,
    ResourceAction,
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
    "PollableClientChannel",
    "EnvelopeKind",
    "TransportEventType",
    "TransportEnvelope",
    "canonicalize_transport_event_type",
    "normalize_transport_event_type",
    "new_envelope_id",
    "Receiver",
    "Sender",
    "AgentControl",
    "ActionHandlerDispatcher",
    "ResourceAction",
    "DefaultAgentChannel",
    "DirectClientChannel",
    "StdioClientChannel",
    "WebSocketClientChannel",
]
