"""Model domain: LLM adapters and response types."""

from dare_framework3_3.model.component import IModelAdapter
from dare_framework3_3.model.types import Message, ModelResponse, GenerateOptions
from dare_framework3_3.model.internal.mock_adapter import MockModelAdapter
from dare_framework3_3.model.internal.openai_adapter import OpenAIModelAdapter

__all__ = [
    "IModelAdapter",
    "Message",
    "ModelResponse",
    "GenerateOptions",
    "MockModelAdapter",
    "OpenAIModelAdapter",
]
