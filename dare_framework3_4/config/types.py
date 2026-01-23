"""config domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConfigSnapshot:
    """Effective configuration snapshot."""

    values: dict[str, Any] = field(default_factory=dict)


__all__ = ["ConfigSnapshot"]

