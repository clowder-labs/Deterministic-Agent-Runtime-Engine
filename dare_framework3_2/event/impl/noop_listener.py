"""No-op event listener implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3_2.event.component import IEventListener

if TYPE_CHECKING:
    from dare_framework3_2.event.types import Event


class NoopListener(IEventListener):
    """A no-op event listener that does nothing.
    
    Useful as a default or for testing.
    """

    async def on_event(self, event: "Event") -> None:
        """Handle an event (no-op)."""
        pass
