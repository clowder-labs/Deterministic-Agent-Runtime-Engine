from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from dare_framework.components.interfaces import IEventLog
from dare_framework.core.events import Event, EventFilter


@dataclass
class InMemoryEventLog(IEventLog):
    def __init__(self) -> None:
        self._events: list[Event] = []

    async def append(self, event: Event) -> str:
        event_id = f"event_{len(self._events) + 1}"
        self._events.append(event)
        return event_id

    async def query(
        self,
        filter: EventFilter | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Event]:
        events: Iterable[Event] = self._events

        if filter:
            if filter.event_types:
                event_types = set(filter.event_types)
                events = [event for event in events if event.event_type in event_types]

            if filter.milestone_id:
                events = [
                    event
                    for event in events
                    if event.payload.get("milestone_id") == filter.milestone_id
                ]

            if filter.since_timestamp is not None:
                events = [
                    event
                    for event in events
                    if event.timestamp >= filter.since_timestamp
                ]

            if filter.until_timestamp is not None:
                events = [
                    event
                    for event in events
                    if event.timestamp <= filter.until_timestamp
                ]

        sliced = list(events)[offset : offset + limit]
        return sliced

    async def verify_chain(self) -> bool:
        return True

    async def get_checkpoint_events(self, checkpoint_id: str) -> list[Event]:
        return [
            event
            for event in self._events
            if event.payload.get("checkpoint_id") == checkpoint_id
        ]
