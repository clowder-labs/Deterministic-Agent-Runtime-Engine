"""hook domain pluggable interfaces (managers)."""

from __future__ import annotations

from typing import Literal, Protocol

from dare_framework.config.types import Config
from dare_framework.hook.kernel import IHook

HookSource = Literal["system", "config", "code"]


class IHookManager(Protocol):
    """Loads hook plugins (multi-load)."""

    def load_hooks(self, *, config: Config | None = None) -> list[IHook]: ...


__all__ = ["HookSource", "IHookManager"]
