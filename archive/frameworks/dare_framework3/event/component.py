"""Event domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework3.event.types import Event, RuntimeSnapshot


class IEventLog(Protocol):
    """WORM truth source for audit and replay."""

    async def append(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        ...

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> Sequence[Event]:
        ...

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        ...

    async def verify_chain(self) -> bool:
        ...


class IEventListener(Protocol):
    """Listener for realtime event notifications."""

    async def on_event(self, event: Event) -> None:
        ...


__all__ = ["IEventLog", "IEventListener"]
