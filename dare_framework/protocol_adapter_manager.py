"""Package-level protocol adapter manager interface.

Temporary placement until a dedicated protocol domain is introduced.
"""

from __future__ import annotations

from typing import Any, Protocol


class IProtocolAdapterManager(Protocol):
    """Loads protocol adapters (multi-load)."""

    def load_protocol_adapters(self, *, config: Any | None = None) -> list[object]: ...


__all__ = ["IProtocolAdapterManager"]
