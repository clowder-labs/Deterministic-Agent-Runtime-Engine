"""model domain facade."""

from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.interfaces import IModelAdapterManager, IPromptLoader, IPromptStore
from dare_framework.model.types import Prompt, ModelInput, ModelResponse, GenerateOptions
from dare_framework.model.factories import (
    create_default_prompt_store,
)
from dare_framework.model.builtin_prompt_loader import BuiltInPromptLoader
from dare_framework.model.filesystem_prompt_loader import FileSystemPromptLoader
from dare_framework.model.layered_prompt_store import LayeredPromptStore
from dare_framework.model.adapters import (
    AnthropicModelAdapter,
    HuaweiModelArtsModelAdapter,
    OpenAIModelAdapter,
    OpenRouterModelAdapter,
)

__all__ = [
    "IModelAdapter",
    "IModelAdapterManager",
    "IPromptLoader",
    "IPromptStore",
    "Prompt",
    "ModelInput",
    "ModelResponse",
    "GenerateOptions",
    "create_default_prompt_store",
    "BuiltInPromptLoader",
    "FileSystemPromptLoader",
    "LayeredPromptStore",
    "AnthropicModelAdapter",
    "HuaweiModelArtsModelAdapter",
    "OpenAIModelAdapter",
    "OpenRouterModelAdapter",
]
