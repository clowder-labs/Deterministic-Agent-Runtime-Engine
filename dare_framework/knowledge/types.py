"""Knowledge domain types and config schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KnowledgeConfig:
    """Configuration for knowledge backend (vector or rawdata + storage).

    Used by create_knowledge() to build IKnowledge from config dict or file.

    type: "vector" | "rawdata"
    storage: "in_memory" | "sqlite" | "chromadb" (vector only for chromadb)
    options: storage-specific (path, host, port, collection_name, etc.)
    """

    type: str = "vector"
    """Knowledge type: "vector" (embedding + similarity) or "rawdata" (content only)."""

    storage: str = "in_memory"
    """Storage backend: "in_memory" | "sqlite" | "chromadb" (chromadb only for vector)."""

    options: dict[str, Any] = field(default_factory=dict)
    """Storage options: path (sqlite), path/host/port/collection_name (chromadb), etc."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeConfig:
        """Build from config dict (e.g. config.knowledge or config file section)."""
        type_ = data.get("type")
        if type_ not in ("vector", "rawdata"):
            type_ = "vector"
        storage = data.get("storage")
        if storage not in ("in_memory", "sqlite", "chromadb"):
            storage = "in_memory"
        options = data.get("options")
        if not isinstance(options, dict):
            options = {}
        # Allow flat keys at top level for convenience (path, host, port, collection_name)
        for key in ("path", "host", "port", "collection_name"):
            if key in data and key not in options:
                options = {**options, key: data[key]}
        return cls(type=type_, storage=storage, options=options)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for config file or logging."""
        return {
            "type": self.type,
            "storage": self.storage,
            "options": dict(self.options),
        }


__all__ = ["KnowledgeConfig"]
