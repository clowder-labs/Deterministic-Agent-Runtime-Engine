"""Event domain kernel interfaces."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework.event.types import Event, RuntimeSnapshot


class IEventLog(Protocol):
    """[Kernel] WORM audit log for event persistence and replay.

    Usage: Called by the agent and control plane to append audit events and replay state.
    """

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        """[Kernel] Append an event record and return its id."""
        ...

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> Sequence[Event]:
        """[Kernel] Query recorded events with optional filters."""
        ...

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        """[Kernel] Replay events starting at an event id."""
        ...

    async def verify_chain(self) -> bool:
        """[Kernel] Verify the event hash chain integrity."""
        ...


__all__ = ["IEventLog"]
