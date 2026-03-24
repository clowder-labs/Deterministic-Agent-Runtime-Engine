"""Model adapters."""

from dare_framework.model.adapters.anthropic_adapter import AnthropicModelAdapter
from dare_framework.model.adapters.huawei_modelarts_adapter import HuaweiModelArtsModelAdapter
from dare_framework.model.adapters.openai_adapter import OpenAIModelAdapter
from dare_framework.model.adapters.openrouter_adapter import OpenRouterModelAdapter

__all__ = [
    "AnthropicModelAdapter",
    "HuaweiModelArtsModelAdapter",
    "OpenAIModelAdapter",
    "OpenRouterModelAdapter",
]
