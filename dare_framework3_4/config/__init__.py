"""config domain facade."""

from __future__ import annotations

from pathlib import Path

from dare_framework3_4.config.kernel import IConfigProvider
from dare_framework3_4.config._internal.file_config_provider import FileConfigProvider
from dare_framework3_4.config.types import (
    ComponentConfig,
    ComponentType,
    Config,
    ConfigSnapshot,
    LLMConfig,
    ProxyConfig,
)

__all__ = [
    "ComponentConfig",
    "ComponentType",
    "Config",
    "ConfigSnapshot",
    "IConfigProvider",
    "LLMConfig",
    "ProxyConfig",
    "FileConfigProvider",
    "build_config_provider",
]


def build_config_provider(
    *,
    workspace_dir: Path | str | None = None,
    user_dir: Path | str | None = None,
) -> IConfigProvider:
    """Create a default file-backed config provider."""
    return FileConfigProvider(
        workspace_dir=workspace_dir,
        user_dir=user_dir,
    )
