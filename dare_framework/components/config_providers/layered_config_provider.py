from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from dare_framework.components.base_component import BaseComponent
from dare_framework.config.config import Config
from dare_framework.config.config_provider import IConfigProvider, build_config_from_layers, merge_config_layers


@dataclass
class LayeredConfigProvider(BaseComponent, IConfigProvider):
    """Config provider that deterministically merges layered config dictionaries.

    Precedence: later layers override earlier layers (system < project < user < session).
    """

    system: dict[str, Any] | None = None
    project: dict[str, Any] | None = None
    user: dict[str, Any] | None = None
    session: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self._refresh()

    @property
    def sources(self) -> dict[str, dict[str, Any]]:
        """Return non-empty raw config sources by name."""
        sources: dict[str, dict[str, Any]] = {}
        if self.system:
            sources["system"] = self.system
        if self.project:
            sources["project"] = self.project
        if self.user:
            sources["user"] = self.user
        if self.session:
            sources["session"] = self.session
        return sources

    @property
    def config_hash(self) -> str:
        """Deterministic hash of the merged config for cache keys and debugging."""
        return self._config_hash

    def current(self) -> Config:
        return self._config

    def reload(self) -> Config:
        self._refresh()
        return self._config

    def get(self, key: str, default: Any | None = None) -> Any:
        """Return value at dotted path from the merged config."""
        current: Any = self._merged
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        value = self.get(namespace)
        return value if isinstance(value, dict) else {}

    def _refresh(self) -> None:
        layers = [self.system or {}, self.project or {}, self.user or {}, self.session or {}]
        self._merged = merge_config_layers(layers)
        self._config = build_config_from_layers([self._merged])
        self._config_hash = _stable_hash(self._merged)


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
