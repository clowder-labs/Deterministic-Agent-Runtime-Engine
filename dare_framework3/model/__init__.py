"""Model domain: LLM adapters and response types."""

from dare_framework3.model.component import IModelAdapter
from dare_framework3.model.types import Message, ModelResponse, GenerateOptions
from dare_framework3.model.impl.mock_adapter import MockModelAdapter
from dare_framework3.model.impl.openai_adapter import OpenAIModelAdapter

__all__ = [
    "IModelAdapter",
    "Message",
    "ModelResponse",
    "GenerateOptions",
    "MockModelAdapter",
    "OpenAIModelAdapter",
]
