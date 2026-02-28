from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from dare_framework.event import DefaultEventLog, Event, RuntimeSnapshot, SQLiteEventLog
from dare_framework.observability._internal.event_trace_bridge import TraceAwareEventLog, make_trace_aware


@pytest.mark.asyncio
async def test_append_query_and_verify_chain(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    event_log = SQLiteEventLog(db_path)

    first_id = await event_log.append("session.start", {"step": 1})
    second_id = await event_log.append("session.end", {"step": 2})

    all_events = await event_log.query(limit=10)
    assert [event.event_id for event in all_events] == [first_id, second_id]

    start_events = await event_log.query(filter={"event_type": "session.start"}, limit=10)
    assert len(start_events) == 1
    assert start_events[0].event_id == first_id

    by_id = await event_log.query(filter={"event_id": second_id}, limit=10)
    assert len(by_id) == 1
    assert by_id[0].event_type == "session.end"

    assert await event_log.verify_chain() is True


@pytest.mark.asyncio
async def test_replay_is_inclusive_and_missing_anchor_fails(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    event_log = SQLiteEventLog(db_path)

    first_id = await event_log.append("a", {"n": 1})
    second_id = await event_log.append("b", {"n": 2})
    _third_id = await event_log.append("c", {"n": 3})

    snapshot = await event_log.replay(from_event_id=second_id)
    assert snapshot.from_event_id == second_id
    assert [event.event_id for event in snapshot.events] == [second_id, _third_id]

    with pytest.raises(ValueError, match="from_event_id"):
        await event_log.replay(from_event_id="missing-id")

    snapshot_first = await event_log.replay(from_event_id=first_id)
    assert len(snapshot_first.events) == 3


@pytest.mark.asyncio
async def test_verify_chain_detects_tampered_row(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    event_log = SQLiteEventLog(db_path)

    await event_log.append("security.check", {"ok": True})
    await event_log.append("security.done", {"ok": True})
    assert await event_log.verify_chain() is True

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE events SET payload_json = ? WHERE seq = 2",
            ('{"ok":false}',),
        )
        conn.commit()

    assert await event_log.verify_chain() is False


@pytest.mark.asyncio
async def test_default_event_log_alias_is_usable(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    event_log = DefaultEventLog(db_path)

    event_id = await event_log.append("default.alias", {"ok": True})
    events = await event_log.query(filter={"event_id": event_id}, limit=10)

    assert len(events) == 1
    assert events[0].event_type == "default.alias"


@pytest.mark.asyncio
async def test_trace_aware_bridge_delegates_for_event_log_contract() -> None:
    class InMemoryEventLog:
        def __init__(self) -> None:
            self.events: list[Event] = []

        async def append(self, event_type: str, payload: dict[str, object]) -> str:
            event = Event(
                event_type=event_type,
                payload=dict(payload),
                timestamp=datetime.now(timezone.utc),
            )
            self.events.append(event)
            return event.event_id

        async def query(
            self,
            *,
            filter: dict[str, object] | None = None,
            limit: int = 100,
        ) -> list[Event]:
            _ = filter
            return self.events[:limit]

        async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
            return RuntimeSnapshot(from_event_id=from_event_id, events=list(self.events))

        async def verify_chain(self) -> bool:
            return True

    base_log = InMemoryEventLog()
    wrapped = make_trace_aware(base_log)
    assert isinstance(wrapped, TraceAwareEventLog)

    event_id = await wrapped.append("trace.test", {"ok": True})
    queried = await wrapped.query(limit=10)
    replayed = await wrapped.replay(from_event_id=event_id)

    assert len(queried) == 1
    assert queried[0].event_id == event_id
    assert replayed.from_event_id == event_id
    assert await wrapped.verify_chain() is True
