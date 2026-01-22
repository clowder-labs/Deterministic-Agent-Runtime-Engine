"""Context domain: context assembly and resource accounting."""

from dare_framework3_3.context.kernel import IContextManager, IResourceManager
from dare_framework3_3.context.component import (
    IAssemblyContext,
    IContextAssembler,
    IContextStrategy,
    IRetrievalContext,
    RetrievalContextAliases,
)
from dare_framework3_3.context.types import (
    AssembledContext,
    AssemblyRequest,
    Context,
    ContextPacket,
    ContextStage,
    IndexStatus,
    Prompt,
    RetrievedContext,
    RetrievalRequest,
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
    "IAssemblyContext",
    "IContextAssembler",
    "IContextStrategy",
    "IRetrievalContext",
    "RetrievalContextAliases",
    "IResourceManager",
    "AssembledContext",
    "AssemblyRequest",
    "Context",
    "ContextPacket",
    "ContextStage",
    "IndexStatus",
    "Prompt",
    "RetrievedContext",
    "RetrievalRequest",
    "RuntimeStateView",
    "SessionContext",
    "Message",
    "Budget",
    "ResourceType",
    "ResourceExhausted",
    "DefaultContextManager",
    "InMemoryResourceManager",
]
