"""Kernel event log protocols (v2)."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework.execution.impl.event.models import Event, RuntimeSnapshot


class IEventLog(Protocol):
    """WORM truth source (v2.0)."""

    async def append(self, event_type: str, payload: dict[str, Any]) -> str: ...

    async def query(self, *, filter: dict[str, Any] | None = None, limit: int = 100) -> Sequence[Event]: ...

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot: ...

    async def verify_chain(self) -> bool: ...
