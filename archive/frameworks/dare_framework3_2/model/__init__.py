"""Model domain: LLM adapter interfaces and implementations.

This domain handles the translation between the framework's
message format and specific LLM provider APIs.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.model.component import IModelAdapter

# Common types
from dare_framework3_2.model.types import Message, ModelResponse, GenerateOptions

# Default implementations
from dare_framework3_2.model.impl.openai_adapter import OpenAIModelAdapter
from dare_framework3_2.model.impl.mock_adapter import MockModelAdapter

__all__ = [
    # Protocol
    "IModelAdapter",
    # Types
    "Message",
    "ModelResponse",
    "GenerateOptions",
    # Implementations
    "OpenAIModelAdapter",
    "MockModelAdapter",
]
