"""Context domain: context assembly and resource accounting."""

from dare_framework3_3.context.kernel import IContextManager, IResourceManager
from dare_framework3_3.context.component import IContextStrategy
from dare_framework3_3.context.types import (
    AssembledContext,
    Context,
    ContextPacket,
    ContextStage,
    IndexStatus,
    Prompt,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
    Message,
    Budget,
    ResourceType,
    ResourceExhausted,
)
from dare_framework3_3.context.internal.default_context_manager import DefaultContextManager
from dare_framework3_3.context.internal.in_memory_resource_manager import InMemoryResourceManager

__all__ = [
    "IContextManager",
    "IContextStrategy",
    "IResourceManager",
    "AssembledContext",
    "Context",
    "ContextPacket",
    "ContextStage",
    "IndexStatus",
    "Prompt",
    "RetrievedContext",
    "RuntimeStateView",
    "SessionContext",
    "Message",
    "Budget",
    "ResourceType",
    "ResourceExhausted",
    "DefaultContextManager",
    "InMemoryResourceManager",
]
