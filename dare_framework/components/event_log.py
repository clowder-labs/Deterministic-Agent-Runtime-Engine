from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..core.interfaces import IEventLog
from ..core.models import Event, EventFilter


class LocalEventLog(IEventLog):
    def __init__(self, path: str = ".dare/event_log.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[Event] = []
        if self._path.exists():
            self._load_existing()

    async def append(self, event: Event) -> str:
        prev_hash = self._events[-1].event_hash if self._events else None
        event = Event(
            event_type=event.event_type,
            payload=event.payload,
            event_id=event.event_id,
            timestamp=event.timestamp,
            prev_hash=prev_hash,
            event_hash=None,
        )
        event_hash = self._hash_event(event)
        event = Event(
            event_type=event.event_type,
            payload=event.payload,
            event_id=event.event_id,
            timestamp=event.timestamp,
            prev_hash=event.prev_hash,
            event_hash=event_hash,
        )
        self._events.append(event)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._serialize(event), sort_keys=True) + "\n")
        return event.event_id

    async def query(self, filter: EventFilter | None = None, offset: int = 0, limit: int = 100) -> list[Event]:
        events = self._events
        if filter:
            events = [
                event
                for event in events
                if (filter.event_type is None or event.event_type == filter.event_type)
                and (
                    filter.milestone_id is None
                    or event.payload.get("milestone_id") == filter.milestone_id
                )
                and (
                    filter.checkpoint_id is None
                    or event.payload.get("checkpoint_id") == filter.checkpoint_id
                )
                and (filter.run_id is None or event.payload.get("run_id") == filter.run_id)
            ]
        return events[offset : offset + limit]

    async def verify_chain(self) -> bool:
        prev_hash = None
        for event in self._events:
            if event.prev_hash != prev_hash:
                return False
            if event.event_hash != self._hash_event(event):
                return False
            prev_hash = event.event_hash
        return True

    async def get_checkpoint_events(self, checkpoint_id: str) -> list[Event]:
        return [
            event
            for event in self._events
            if event.payload.get("checkpoint_id") == checkpoint_id
        ]

    def _hash_event(self, event: Event) -> str:
        payload = json.dumps(self._serialize(event, include_hash=False), sort_keys=True)
        return sha256(payload.encode("utf-8")).hexdigest()

    def _serialize(self, event: Event, include_hash: bool = True) -> dict[str, Any]:
        data = asdict(event)
        data["timestamp"] = event.timestamp.isoformat()
        if not include_hash:
            data["event_hash"] = None
        return data

    def _load_existing(self) -> None:
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                event = Event(
                    event_type=record["event_type"],
                    payload=record["payload"],
                    event_id=record["event_id"],
                    timestamp=_parse_timestamp(record["timestamp"]),
                    prev_hash=record.get("prev_hash"),
                    event_hash=record.get("event_hash"),
                )
                self._events.append(event)


def _parse_timestamp(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
