"""Memory components (Layer 2).

Memory is an optional capability in early v2 milestones. The Kernel `IContextManager`
is responsible for orchestration; memory implementations provide retrieval primitives.
"""

from dare_framework.components.memory.noop import NoOpMemory
from dare_framework.components.memory.protocols import IMemory

__all__ = [
    "IMemory",
    "NoOpMemory",
]

