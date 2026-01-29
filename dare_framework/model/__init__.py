"""model domain facade."""

from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.interfaces import IModelAdapterManager, IPromptLoader, IPromptStore
from dare_framework.model.types import Prompt, ModelInput, ModelResponse, GenerateOptions
from dare_framework.model._internal.builtin_prompt_loader import BuiltInPromptLoader
from dare_framework.model._internal.filesystem_prompt_loader import FileSystemPromptLoader
from dare_framework.model._internal.layered_prompt_store import LayeredPromptStore
from dare_framework.model._internal.openai_adapter import OpenAIModelAdapter

__all__ = [
    "IModelAdapter",
    "IModelAdapterManager",
    "IPromptLoader",
    "IPromptStore",
    "Prompt",
    "ModelInput",
    "ModelResponse",
    "GenerateOptions",
    "BuiltInPromptLoader",
    "FileSystemPromptLoader",
    "LayeredPromptStore",
    "OpenAIModelAdapter",
]
