"""memory domain facade."""

from dare_framework.memory.kernel import ILongTermMemory, IShortTermMemory
from dare_framework.memory.types import LongTermMemoryConfig
from dare_framework.memory.factory import create_long_term_memory
from dare_framework.memory._internal.in_memory_stm import InMemorySTM
from dare_framework.memory._internal.rawdata_ltm import RawDataLongTermMemory
from dare_framework.memory._internal.vector_ltm import VectorLongTermMemory

__all__ = [
    "IShortTermMemory",
    "ILongTermMemory",
    "InMemorySTM",
    "LongTermMemoryConfig",
    "create_long_term_memory",
    "RawDataLongTermMemory",
    "VectorLongTermMemory",
]
