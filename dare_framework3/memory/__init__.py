"""Memory domain: storage and prompt templates."""

from dare_framework3.memory.component import IMemory, IPromptStore
from dare_framework3.memory.impl.noop_memory import NoOpMemory
from dare_framework3.memory.impl.noop_prompt_store import NoOpPromptStore

__all__ = [
    "IMemory",
    "IPromptStore",
    "NoOpMemory",
    "NoOpPromptStore",
]
