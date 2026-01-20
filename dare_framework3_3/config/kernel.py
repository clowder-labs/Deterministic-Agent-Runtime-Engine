"""Config domain kernel interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework3_3.config.types import Config


@runtime_checkable
class IConfigProvider(Protocol):
    """[Kernel] Provides resolved configuration and supports reload.

    Usage: Called by the agent to access effective configuration layers.
    """

    def current(self) -> Config:
        """[Kernel] Return the current resolved configuration.

        Usage: Called by components to read config values.
        """
        ...

    def reload(self) -> Config:
        """[Kernel] Reload configuration sources and return the result.

        Usage: Called by tooling or hot-reload workflows.
        """
        ...


__all__ = ["IConfigProvider"]
