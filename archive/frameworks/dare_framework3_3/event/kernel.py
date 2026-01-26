"""Event domain kernel interfaces."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework3_3.event.types import Event, RuntimeSnapshot


class IEventLog(Protocol):
    """[Kernel] WORM audit log for event persistence and replay.

    Usage: Called by the agent to append events and replay execution state.
    """

    async def append(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """[Kernel] Append an event record and return its id.

        Usage: Called at key execution milestones for audit logging.
        """
        ...

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> Sequence[Event]:
        """[Kernel] Query recorded events with optional filters.

        Usage: Called by inspection or analysis tools.
        """
        ...

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        """[Kernel] Replay events starting at an event id.

        Usage: Called to reconstruct execution state.
        """
        ...

    async def verify_chain(self) -> bool:
        """[Kernel] Verify the event hash chain integrity.

        Usage: Called by audit tooling to validate log integrity.
        """
        ...


__all__ = ["IEventLog"]
