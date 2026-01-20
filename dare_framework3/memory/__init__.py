"""Memory domain: storage and retrieval of historical information.

This domain handles persistent storage and retrieval of context,
facts, and historical information for the agent.

Factory Functions:
    create_noop_memory: Create a no-op IMemory implementation
    create_noop_prompt_store: Create a no-op IPromptStore implementation
"""

from __future__ import annotations

from dare_framework3.memory.interfaces import IMemory, IPromptStore

__all__ = [
    # Interfaces
    "IMemory",
    "IPromptStore",
    # Factory functions
    "create_noop_memory",
    "create_noop_prompt_store",
]


# =============================================================================
# Factory Functions
# =============================================================================

def create_noop_memory() -> IMemory:
    """Create a no-op IMemory implementation.
    
    Returns:
        A NoOpMemory instance (placeholder)
    """
    from dare_framework3.memory.impl.noop_memory import NoOpMemory
    return NoOpMemory()


def create_noop_prompt_store() -> IPromptStore:
    """Create a no-op IPromptStore implementation.
    
    Returns:
        A NoOpPromptStore instance (placeholder)
    """
    from dare_framework3.memory.impl.noop_prompt_store import NoOpPromptStore
    return NoOpPromptStore()
