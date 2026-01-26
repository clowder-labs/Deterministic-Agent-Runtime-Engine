"""model domain facade."""

from dare_framework.model.interfaces import IModelAdapter, IModelAdapterManager
from dare_framework.model.types import Prompt, ModelResponse, GenerateOptions
from dare_framework.model._internal.openai_adapter import OpenAIModelAdapter

__all__ = [
    "IModelAdapter",
    "IModelAdapterManager",
    "Prompt",
    "ModelResponse",
    "GenerateOptions",
    "OpenAIModelAdapter",
]
