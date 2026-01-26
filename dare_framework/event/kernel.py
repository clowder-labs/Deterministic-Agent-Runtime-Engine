"""event domain stable interfaces.

Alignment notes:
- EventLog is append-only (WORM) and supports query + replay.
- Hash-chain integrity verification is optional.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework.event.types import Event, RuntimeSnapshot


class IEventLog(Protocol):
    """Append-only audit log for event persistence and replay."""

    async def append(self, event_type: str, payload: dict[str, Any]) -> str: ...

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> Sequence[Event]: ...

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot: ...


class IHashChainEventLog(IEventLog, Protocol):
    """Optional extension for logs that support hash-chain verification."""

    async def verify_chain(self) -> bool: ...


__all__ = ["IEventLog", "IHashChainEventLog"]
