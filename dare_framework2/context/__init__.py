"""Context domain: what information enters the LLM window.

This domain handles context engineering - deciding what information
should be included in the LLM's context window, with explainable
attribution and budget management.
"""

from dare_framework2.context.interfaces import IContextManager, IContextStrategy
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
