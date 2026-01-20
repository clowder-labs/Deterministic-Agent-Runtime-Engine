"""Event domain component interfaces."""

from __future__ import annotations

from typing import Protocol

from dare_framework3_3.event.types import Event


class IEventListener(Protocol):
    """[Component] Listener for realtime event notifications.

    Usage: Registered by integrations to stream event updates.
    """

    async def on_event(self, event: Event) -> None:
        """[Component] Handle a single event notification.

        Usage: Called by the event log implementation after append.
        """
        ...


__all__ = ["IEventListener"]
