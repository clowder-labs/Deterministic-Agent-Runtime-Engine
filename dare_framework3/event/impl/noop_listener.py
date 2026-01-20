"""No-op event listener implementation."""

from __future__ import annotations

from dare_framework3.event.component import IEventListener
from dare_framework3.event.types import Event


class NoOpListener(IEventListener):
    """Event listener that ignores all events."""

    async def on_event(self, event: Event) -> None:
        _ = event
