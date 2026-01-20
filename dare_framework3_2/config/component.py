"""Config domain component interfaces (Protocol definitions)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework3_2.config.types import Config


@runtime_checkable
class IConfigProvider(Protocol):
    """Provides resolved configuration and supports reload.
    
    Implementations may load configuration from files, environment
    variables, or other sources.
    """

    def current(self) -> Config:
        """Return the current effective configuration.
        
        Returns:
            The current configuration
        """
        ...

    def reload(self) -> Config:
        """Reload configuration and return the effective result.
        
        Returns:
            The reloaded configuration
        """
        ...
