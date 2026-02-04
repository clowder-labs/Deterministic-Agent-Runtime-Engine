"""config domain facade."""

from __future__ import annotations

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.factory import build_config_provider
from dare_framework.config.file_config_provider import FileConfigProvider
from dare_framework.config.types import (
    ComponentConfig,
    Config,
    LLMConfig,
    ObservabilityConfig,
    ProxyConfig,
    RedactionConfig,
)

__all__ = [
    "ComponentConfig",
    "Config",
    "IConfigProvider",
    "LLMConfig",
    "ObservabilityConfig",
    "ProxyConfig",
    "RedactionConfig",
    "FileConfigProvider",
    "build_config_provider",
]
