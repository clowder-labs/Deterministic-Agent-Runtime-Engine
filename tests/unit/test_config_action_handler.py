from __future__ import annotations

import sys

import pytest

if sys.version_info >= (3, 14):
    pytest.skip(
        "Skipping config action handler tests on Python 3.14 due infra.protocol runtime-check issue",
        allow_module_level=True,
    )

from dare_framework.config._internal.action_handler import ConfigActionHandler
from dare_framework.config.types import Config
from dare_framework.transport.interaction.resource_action import ResourceAction


class _DummyConfigProvider:
    def __init__(self, config: Config) -> None:
        self._config = config

    def current(self) -> Config:
        return self._config

    def reload(self) -> Config:
        return self._config


@pytest.mark.asyncio
async def test_config_action_handler_prefers_explicit_config() -> None:
    explicit = Config(workspace_dir="/explicit/workspace")
    provider = _DummyConfigProvider(Config(workspace_dir="/provider/workspace"))
    handler = ConfigActionHandler(config=explicit, manager=provider)

    result = await handler.invoke(ResourceAction.CONFIG_GET, {})

    assert result["workspace_dir"] == "/explicit/workspace"


@pytest.mark.asyncio
async def test_config_action_handler_uses_provider_when_config_missing() -> None:
    provider = _DummyConfigProvider(Config(workspace_dir="/provider/workspace"))
    handler = ConfigActionHandler(config=None, manager=provider)

    result = await handler.invoke(ResourceAction.CONFIG_GET, {})

    assert result["workspace_dir"] == "/provider/workspace"
