"""context domain facade."""

from dare_framework.context.kernel import IContext, IAssembleContext, IRetrievalContext
from dare_framework.context.types import (
    AssembledContext,
    AttachmentKind,
    AttachmentRef,
    Budget,
    Message,
    MessageKind,
    MessageMark,
    MessageRole,
)
from dare_framework.context.context import Context
from dare_framework.context.smartcontext import SmartContext

__all__ = [
    "Context",
    "SmartContext",
    "AssembledContext",
    "AttachmentKind",
    "AttachmentRef",
    "Budget",
    "IContext",
    "IRetrievalContext",
    "Message",
    "MessageKind",
    "MessageMark",
    "MessageRole",
    "IAssembleContext",
]
