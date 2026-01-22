"""Memory domain: short-term and long-term memory interfaces."""

from dare_framework3_4.memory.component import IShortTermMemory, ILongTermMemory
from dare_framework3_4.memory.internal.in_memory_stm import InMemorySTM

__all__ = [
    # Interfaces
    "IShortTermMemory",
    "ILongTermMemory",
    # Implementations
    "InMemorySTM",
]
