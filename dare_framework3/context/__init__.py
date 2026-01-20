"""Context domain: what information enters the LLM window.

This domain handles context engineering - deciding what information
should be included in the LLM's context window, with explainable
attribution and budget management.

Factory Functions:
    create_default_context_manager: Create default IContextManager
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3.context.interfaces import IContextManager, IContextStrategy
from dare_framework3.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    Prompt,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
)

if TYPE_CHECKING:
    from dare_framework3.memory.interfaces import IMemory

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
    # Factory functions
    "create_default_context_manager",
]


# =============================================================================
# Factory Functions
# =============================================================================

def create_default_context_manager(
    memory: "IMemory | None" = None,
) -> IContextManager:
    """Create the default IContextManager implementation.
    
    Args:
        memory: Optional memory component for context retrieval
        
    Returns:
        A DefaultContextManager instance
    """
    from dare_framework3.context.impl.default_context_manager import DefaultContextManager
    return DefaultContextManager(memory=memory)
