"""Config domain component interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework3.config.types import Config


@runtime_checkable
class IConfigProvider(Protocol):
    """Provides resolved configuration and supports reload."""

    def current(self) -> Config:
        ...

    def reload(self) -> Config:
        ...


__all__ = ["IConfigProvider"]
