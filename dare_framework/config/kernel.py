"""config domain stable interfaces."""

from __future__ import annotations

from typing import Protocol

from dare_framework.config.types import Config


class IConfigProvider(Protocol):
    def current(self) -> Config: ...

    def reload(self) -> Config: ...


__all__ = ["IConfigProvider"]
