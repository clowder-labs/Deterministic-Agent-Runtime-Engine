"""Model domain: model adapter interfaces."""

from dare_framework3_4.model.component import IModelAdapter
from dare_framework3_4.model.types import Prompt, ModelResponse, GenerateOptions
from dare_framework3_4.model.internal.openai_adapter import OpenAIModelAdapter

__all__ = [
    "IModelAdapter",
    "Prompt",
    "ModelResponse",
    "GenerateOptions",
    "OpenAIModelAdapter",
]
