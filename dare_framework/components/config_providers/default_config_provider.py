from __future__ import annotations

from typing import Any

from dare_framework.config.config import Config
from dare_framework.config.config_provider import IConfigProvider
from ..base_component import BaseComponent


class DefaultConfigProvider(BaseComponent, IConfigProvider):
    def __init__(self, config: Config | dict[str, Any] | None = None) -> None:
        if isinstance(config, Config):
            self._config = config
            self._raw = config.to_dict()
        else:
            self._raw = config or {}
            self._config = Config.from_dict(self._raw)

    def current(self) -> Config:
        return self._config

    def reload(self) -> Config:
        self._config = Config.from_dict(self._raw)
        return self._config

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._raw.get(key, default)

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        prefix = f"{namespace}." if namespace else ""
        return {
            key[len(prefix):]: value
            for key, value in self._raw.items()
            if key.startswith(prefix)
        }
