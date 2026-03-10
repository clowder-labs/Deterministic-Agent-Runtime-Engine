"""transport domain facade."""

from dare_framework.transport.interfaces import AgentChannel, ClientChannel, PollableClientChannel
from dare_framework.transport.serialization import jsonify_transport_value
from dare_framework.transport.types import (
    ActionPayload,
    ControlPayload,
    EnvelopePayload,
    EnvelopeKind,
    MessageRole,
    MessageKind,
    MessagePayload,
    AttachmentRef,
    SelectDomain,
    SelectKind,
    SelectPayload,
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
    "PollableClientChannel",
    "jsonify_transport_value",
    "EnvelopePayload",
    "EnvelopeKind",
    "AttachmentRef",
    "MessageRole",
    "MessageKind",
    "MessagePayload",
    "SelectKind",
    "SelectDomain",
    "SelectPayload",
    "ActionPayload",
    "ControlPayload",
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
