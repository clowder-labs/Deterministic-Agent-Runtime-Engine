"""config domain stable interfaces."""

from __future__ import annotations

from typing import Protocol

from dare_framework3_4.config.types import ConfigSnapshot


class IConfigProvider(Protocol):
    def current(self) -> ConfigSnapshot: ...

    def reload(self) -> ConfigSnapshot: ...


__all__ = ["IConfigProvider"]

