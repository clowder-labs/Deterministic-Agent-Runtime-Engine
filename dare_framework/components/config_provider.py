from __future__ import annotations

from typing import Any

from ..core.interfaces import IConfigProvider
from .base_component import BaseComponent


class StaticConfigProvider(BaseComponent, IConfigProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._config.get(key, default)

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        prefix = f"{namespace}." if namespace else ""
        return {
            key[len(prefix) :]: value
            for key, value in self._config.items()
            if key.startswith(prefix)
        }
