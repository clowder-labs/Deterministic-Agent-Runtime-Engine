"""File-backed config provider implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.types import Config, ConfigSnapshot


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _merge_layers(layers: Iterable[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for layer in layers:
        merged = _deep_merge(merged, layer)
    return merged


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")
    return payload


def _find_project_root(start: Path) -> Path:
    """Return the nearest ancestor that looks like a project root."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


@dataclass
class FileConfigProvider(IConfigProvider):
    """Load config from user and workspace directories (JSON)."""

    workspace_dir: Path | str | None = None
    user_dir: Path | str | None = None
    filename: str = ".dare/config.json"

    def __post_init__(self) -> None:
        if self.workspace_dir:
            self._workspace_dir = Path(self.workspace_dir)
        else:
            # Prefer repository root when called from a subdirectory.
            self._workspace_dir = _find_project_root(Path.cwd())
        self._user_dir = Path(self.user_dir) if self.user_dir else Path.home()
        self._snapshot = self._load_snapshot()

    def current(self) -> ConfigSnapshot:
        return self._snapshot

    def reload(self) -> ConfigSnapshot:
        self._snapshot = self._load_snapshot()
        return self._snapshot

    def _load_snapshot(self) -> ConfigSnapshot:
        user_layer = self._load_layer(self._user_dir)
        workspace_layer = self._load_layer(self._workspace_dir)
        merged = _merge_layers([user_layer, workspace_layer])
        merged.setdefault("workspace_dir", str(self._workspace_dir))
        merged.setdefault("user_dir", str(self._user_dir))
        config = Config.from_dict(merged)
        return ConfigSnapshot(config=config)

    def _load_layer(self, base_dir: Path) -> dict[str, Any]:
        path = base_dir / self.filename
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
            return {}
        return _load_json(path)


__all__ = ["FileConfigProvider"]
