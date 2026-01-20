"""Context domain: context engineering and resource management.

This domain handles context assembly for LLM prompts,
retrieval operations, and resource/budget management.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.context.component import (
    IContextManager,
    IContextStrategy,
    IResourceManager,
)

# Common types (users may construct or use for type annotations)
from dare_framework3_2.context.types import (
    ContextStage,
    AssembledContext,
    Budget,
    ResourceType,
    ResourceExhausted,
)

# Default implementations
from dare_framework3_2.context.impl.default_context_manager import DefaultContextManager
from dare_framework3_2.context.impl.in_memory_resource_manager import InMemoryResourceManager

__all__ = [
    # Protocol
    "IContextManager",
    "IContextStrategy",
    "IResourceManager",
    # Types
    "ContextStage",
    "AssembledContext",
    "Budget",
    "ResourceType",
    "ResourceExhausted",
    # Implementations
    "DefaultContextManager",
    "InMemoryResourceManager",
]
