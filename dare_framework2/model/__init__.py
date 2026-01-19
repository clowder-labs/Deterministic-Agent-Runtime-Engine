"""Model domain: LLM interaction abstraction.

This domain handles all interactions with Large Language Models,
providing a unified interface regardless of the underlying provider.
"""

from dare_framework2.model.interfaces import IModelAdapter
from dare_framework2.model.types import Message, ModelResponse, GenerateOptions

__all__ = [
    # Interfaces
    "IModelAdapter",
    # Types
    "Message",
    "ModelResponse",
    "GenerateOptions",
]
