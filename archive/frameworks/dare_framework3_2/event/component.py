"""Event domain component interfaces (Protocol definitions)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence

if TYPE_CHECKING:
    from dare_framework3_2.event.types import Event, RuntimeSnapshot


class IEventLog(Protocol):
    """WORM truth source for audit and replay.
    
    Provides append-only event logging with chain integrity verification.
    """

    async def append(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Append an event to the log.
        
        Args:
            event_type: Type of event
            payload: Event data
            
        Returns:
            Event ID
        """
        ...

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> Sequence["Event"]:
        """Query events from the log.
        
        Args:
            filter: Optional filter criteria
            limit: Maximum events to return
            
        Returns:
            Matching events
        """
        ...

    async def replay(self, *, from_event_id: str) -> "RuntimeSnapshot":
        """Create a replay snapshot from an event.
        
        Args:
            from_event_id: Starting event ID
            
        Returns:
            Runtime snapshot for replay
        """
        ...

    async def verify_chain(self) -> bool:
        """Verify the integrity of the event chain.
        
        Returns:
            True if chain is valid
        """
        ...


class IEventListener(Protocol):
    """Real-time event listener.
    
    Receives events as they are appended to the event log.
    """

    async def on_event(self, event: "Event") -> None:
        """Handle an event.
        
        Args:
            event: The event to handle
        """
        ...
