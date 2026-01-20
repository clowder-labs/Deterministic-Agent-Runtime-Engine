"""Memory domain: storage and retrieval of historical information.

This domain handles persistent storage and retrieval of context,
facts, and historical information for the agent.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.memory.component import IMemory, IPromptStore

# Default implementations
from dare_framework3_2.memory.impl.noop_memory import NoOpMemory
from dare_framework3_2.memory.impl.noop_prompt_store import NoOpPromptStore

__all__ = [
    # Protocol
    "IMemory",
    "IPromptStore",
    # Implementations
    "NoOpMemory",
    "NoOpPromptStore",
]
