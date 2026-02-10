"""transport domain facade."""

from dare_framework.transport.interfaces import AgentChannel, ClientChannel
from dare_framework.transport.types import (
    EnvelopeKind,
    TransportEnvelope,
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
    "EnvelopeKind",
    "TransportEnvelope",
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
