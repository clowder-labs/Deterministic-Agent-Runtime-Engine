"""hook domain pluggable interfaces (managers)."""

from __future__ import annotations

from typing import Any, Protocol


class IHookManager(Protocol):
    """Loads hook plugins (multi-load)."""

    def load_hooks(self, *, config: Any | None = None) -> list[object]: ...


__all__ = ["IHookManager"]
