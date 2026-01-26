from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Sequence

from dare_framework.execution.impl.event.models import Event, RuntimeSnapshot
from dare_framework.execution.impl.event.protocols import IEventLog


class LocalEventLog(IEventLog):
    """Local append-only JSONL event log with a hash chain (WORM-friendly)."""

    def __init__(self, path: str = ".dare/event_log.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[Event] = []
        if self._path.exists():
            self._load_existing()

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        prev_hash = self._events[-1].event_hash if self._events else None
        event = Event(event_type=event_type, payload=payload, prev_hash=prev_hash, event_hash=None)
        event_hash = self._hash_event(event)
        sealed = Event(
            event_type=event.event_type,
            payload=event.payload,
            event_id=event.event_id,
            timestamp=event.timestamp,
            prev_hash=event.prev_hash,
            event_hash=event_hash,
        )
        self._events.append(sealed)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._serialize(sealed), sort_keys=True) + "\n")
        return sealed.event_id

    async def query(self, *, filter: dict[str, Any] | None = None, limit: int = 100) -> Sequence[Event]:
        events = self._events
        if filter:
            want_type = filter.get("event_type")
            want_run_id = filter.get("run_id")
            want_milestone_id = filter.get("milestone_id")
            want_checkpoint_id = filter.get("checkpoint_id")

            def _match(item: Event) -> bool:
                if want_type is not None and item.event_type != want_type:
                    return False
                if want_run_id is not None and item.payload.get("run_id") != want_run_id:
                    return False
                if want_milestone_id is not None and item.payload.get("milestone_id") != want_milestone_id:
                    return False
                if want_checkpoint_id is not None and item.payload.get("checkpoint_id") != want_checkpoint_id:
                    return False
                return True

            events = [event for event in events if _match(event)]
        return events[:limit]

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        start_index = next(
            (index for index, event in enumerate(self._events) if event.event_id == from_event_id),
            None,
        )
        if start_index is None:
            raise ValueError(f"Unknown event id: {from_event_id}")
        return RuntimeSnapshot(from_event_id=from_event_id, events=self._events[start_index:])

    async def verify_chain(self) -> bool:
        prev_hash = None
        for event in self._events:
            if event.prev_hash != prev_hash:
                return False
            if event.event_hash != self._hash_event(event):
                return False
            prev_hash = event.event_hash
        return True

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
                self._events.append(
                    Event(
                        event_type=record["event_type"],
                        payload=record["payload"],
                        event_id=record["event_id"],
                        timestamp=_parse_timestamp(record["timestamp"]),
                        prev_hash=record.get("prev_hash"),
                        event_hash=record.get("event_hash"),
                    )
                )


def _parse_timestamp(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
