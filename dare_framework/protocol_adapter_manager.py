"""Package-level protocol adapter manager interface.

Temporary placement until a dedicated protocol domain is introduced.
"""

from __future__ import annotations

from typing import Protocol

from dare_framework.config.types import Config
from dare_framework.tool.interfaces import IProtocolAdapter


class IProtocolAdapterManager(Protocol):
    """Loads protocol adapters (multi-load)."""

    def load_protocol_adapters(self, *, config: Config | None = None) -> list[IProtocolAdapter]: ...


__all__ = ["IProtocolAdapterManager"]
