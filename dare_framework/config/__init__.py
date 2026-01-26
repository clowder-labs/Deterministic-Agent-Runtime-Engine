"""config domain facade."""

from __future__ import annotations

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config._internal.file_config_provider import FileConfigProvider
from dare_framework.config.factory import build_config_provider
from dare_framework.infra.component import ComponentType
from dare_framework.config.types import (
    ComponentConfig,
    Config,
    LLMConfig,
    ProxyConfig,
)

__all__ = [
    "ComponentConfig",
    "ComponentType",
    "Config",
    "IConfigProvider",
    "LLMConfig",
    "ProxyConfig",
    "FileConfigProvider",
    "build_config_provider",
]
