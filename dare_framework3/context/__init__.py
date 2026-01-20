"""Context domain: context assembly and resource accounting."""

from dare_framework3.context.component import IContextManager, IContextStrategy, IResourceManager
from dare_framework3.context.types import (
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
from dare_framework3.context.impl.default_context_manager import DefaultContextManager
from dare_framework3.context.impl.in_memory_resource_manager import InMemoryResourceManager

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
