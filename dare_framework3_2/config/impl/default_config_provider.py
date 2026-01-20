"""Default config provider implementation."""

from __future__ import annotations

from dare_framework3_2.config.component import IConfigProvider
from dare_framework3_2.config.types import Config


class DefaultConfigProvider(IConfigProvider):
    """A simple config provider with a fixed configuration.
    
    Useful for testing or when configuration is provided programmatically.
    
    Args:
        config: The configuration to provide
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()

    def current(self) -> Config:
        """Return the current configuration."""
        return self._config

    def reload(self) -> Config:
        """Return the current configuration (no reload for fixed config)."""
        return self._config
