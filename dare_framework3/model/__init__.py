"""Model domain: LLM adapter interfaces and implementations."""

from dare_framework3.model.interfaces import IModelAdapter
from dare_framework3.model.types import Message, ModelResponse, GenerateOptions

__all__ = [
    # Interfaces
    "IModelAdapter",
    # Types
    "Message",
    "ModelResponse",
    "GenerateOptions",
]
