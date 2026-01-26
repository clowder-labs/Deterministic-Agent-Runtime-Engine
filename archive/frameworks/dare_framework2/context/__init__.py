"""Context domain: what information enters the LLM window.

This domain handles context engineering - deciding what information
should be included in the LLM's context window, with explainable
attribution and budget management.
"""

from dare_framework2.context.kernel import IContextManager
from dare_framework2.context.components import (
    IContextStrategy,
    IMemory,
    IPromptStore,
    IRetriever,
    IIndexer,
)
from dare_framework2.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    Prompt,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
)

__all__ = [
    # Interfaces
    "IContextManager",
    "IContextStrategy",
    "IMemory",
    "IPromptStore",
    "IRetriever",
    "IIndexer",
    # Types
    "AssembledContext",
    "ContextPacket",
    "ContextStage",
    "IndexStatus",
    "Prompt",
    "RetrievedContext",
    "RuntimeStateView",
    "SessionContext",
]
