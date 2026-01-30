from __future__ import annotations

import pytest

from dare_framework.builder import Builder
from dare_framework.config.types import Config, LLMConfig
from dare_framework.model import (
    OpenAIModelAdapter,
    OpenRouterModelAdapter,
    create_default_model_adapter_manager,
)


def test_default_manager_returns_openai_adapter() -> None:
    manager = create_default_model_adapter_manager()
    adapter = manager.load_model_adapter(config=Config())
    assert isinstance(adapter, OpenAIModelAdapter)
    assert adapter.name == "openai"


def test_default_manager_returns_openrouter_adapter() -> None:
    manager = create_default_model_adapter_manager()
    config = Config(llm=LLMConfig(adapter="openrouter", api_key="test-key", model="openrouter/test"))
    adapter = manager.load_model_adapter(config=config)
    assert isinstance(adapter, OpenRouterModelAdapter)
    assert adapter.name == "openrouter"
    assert adapter.model_name == "openrouter/test"


def test_default_manager_unsupported_adapter_raises() -> None:
    manager = create_default_model_adapter_manager()
    config = Config(llm=LLMConfig(adapter="unknown"))
    with pytest.raises(ValueError, match="Unsupported model adapter"):
        manager.load_model_adapter(config=config)


def test_builder_uses_default_manager_when_missing() -> None:
    config = Config()
    agent = Builder.simple_chat_agent_builder("default-manager-test").with_config(config).build()
    model = getattr(agent, "_model", None)
    assert isinstance(model, OpenAIModelAdapter)
