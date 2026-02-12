from __future__ import annotations

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.config.types import Config, LLMConfig
from dare_framework.model import OpenAIModelAdapter, OpenRouterModelAdapter
from dare_framework.model.default_model_adapter_manager import DefaultModelAdapterManager


def test_default_manager_returns_openai_adapter() -> None:
    manager = DefaultModelAdapterManager()
    adapter = manager.load_model_adapter(config=Config())
    assert isinstance(adapter, OpenAIModelAdapter)
    assert adapter.name == "openai"


def test_default_manager_returns_openrouter_adapter() -> None:
    manager = DefaultModelAdapterManager()
    config = Config(llm=LLMConfig(adapter="openrouter", api_key="test-key", model="openrouter/test"))
    adapter = manager.load_model_adapter(config=config)
    assert isinstance(adapter, OpenRouterModelAdapter)
    assert adapter.name == "openrouter"
    assert adapter.model_name == "openrouter/test"


def test_default_manager_unsupported_adapter_raises() -> None:
    manager = DefaultModelAdapterManager()
    config = Config(llm=LLMConfig(adapter="unknown"))
    with pytest.raises(ValueError, match="Unsupported model adapter"):
        manager.load_model_adapter(config=config)


def test_default_manager_requires_config_when_none_provided() -> None:
    manager = DefaultModelAdapterManager()
    with pytest.raises(ValueError, match="requires a Config"):
        manager.load_model_adapter()


@pytest.mark.asyncio
async def test_builder_uses_default_manager_when_missing() -> None:
    config = Config()
    agent = await BaseAgent.simple_chat_agent_builder("default-manager-test").with_config(config).build()
    model = getattr(agent, "_model", None)
    assert isinstance(model, OpenAIModelAdapter)
