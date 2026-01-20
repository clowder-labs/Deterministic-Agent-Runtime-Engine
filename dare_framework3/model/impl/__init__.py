"""Model domain implementations."""

from dare_framework3.model.impl.mock_adapter import MockModelAdapter
from dare_framework3.model.impl.openai_adapter import OpenAIModelAdapter

__all__ = [
    "MockModelAdapter",
    "OpenAIModelAdapter",
]
