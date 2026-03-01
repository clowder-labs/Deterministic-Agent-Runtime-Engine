from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone

import pytest

from dare_framework.event import DefaultEventLog, Event, RuntimeSnapshot, SQLiteEventLog
from dare_framework.observability._internal.event_trace_bridge import (
    TraceAwareEventLog,
    TraceContext,
    make_trace_aware,
)


def _hash_v1(
    *,
    event_id: str,
    event_type: str,
    timestamp_iso: str,
    payload_json: str,
    prev_hash: str | None,
) -> str:
    prev_segment = prev_hash or ""
    raw = "\n".join([event_id, event_type, timestamp_iso, payload_json, prev_segment])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
async def test_append_persists_hash_version_column(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    event_log = SQLiteEventLog(db_path)

    event_id = await event_log.append("hash.version", {"ok": True})
    assert event_id

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT hash_version FROM events WHERE event_id = ?", (event_id,)).fetchone()
    assert row is not None
    assert int(row[0]) == 1


@pytest.mark.asyncio
async def test_verify_chain_returns_false_for_unsupported_hash_version(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    event_log = SQLiteEventLog(db_path)

    await event_log.append("security.check", {"ok": True})
    await event_log.append("security.done", {"ok": True})
    assert await event_log.verify_chain() is True

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE events SET hash_version = ? WHERE seq = 2", (999,))
        conn.commit()

    assert await event_log.verify_chain() is False


@pytest.mark.asyncio
async def test_schema_migrates_legacy_events_table_with_hash_version(tmp_path) -> None:
    db_path = tmp_path / "legacy-events.db"
    event_id = "legacy-e1"
    event_type = "legacy.start"
    payload_json = '{"n":1}'
    timestamp_iso = "2026-03-01T00:00:00+00:00"
    event_hash = _hash_v1(
        event_id=event_id,
        event_type=event_type,
        timestamp_iso=timestamp_iso,
        payload_json=payload_json,
        prev_hash=None,
    )

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                timestamp_iso TEXT NOT NULL,
                prev_hash TEXT,
                event_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            (
                "INSERT INTO events (event_id, event_type, payload_json, timestamp_iso, prev_hash, event_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (event_id, event_type, payload_json, timestamp_iso, None, event_hash),
        )
        conn.commit()

    event_log = SQLiteEventLog(db_path)
    assert await event_log.verify_chain() is True

    with sqlite3.connect(db_path) as conn:
        columns = conn.execute("PRAGMA table_info(events)").fetchall()
        names = {str(row[1]) for row in columns}
        migrated = conn.execute(
            "SELECT hash_version FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    assert "hash_version" in names
    assert migrated is not None
    assert int(migrated[0]) == 1


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


@pytest.mark.asyncio
async def test_trace_aware_bridge_persists_trace_context_to_sqlite_payload(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "events.db"
    base_log = SQLiteEventLog(db_path)

    monkeypatch.setattr(
        "dare_framework.observability._internal.event_trace_bridge.extract_trace_context",
        lambda: TraceContext(
            trace_id="trace-123",
            span_id="span-456",
            trace_flags=1,
        ),
    )

    wrapped = make_trace_aware(base_log)
    event_id = await wrapped.append("trace.bridge", {"ok": True})

    queried = await base_log.query(filter={"event_id": event_id}, limit=1)
    assert len(queried) == 1
    trace_payload = queried[0].payload.get("_trace")
    assert trace_payload == {
        "trace_id": "trace-123",
        "span_id": "span-456",
        "trace_flags": 1,
    }
    assert queried[0].payload.get("trace_id") == "trace-123"
    assert queried[0].payload.get("span_id") == "span-456"
    assert queried[0].payload.get("trace_flags") == 1

    snapshot = await base_log.replay(from_event_id=event_id)
    assert snapshot.events[0].payload.get("_trace") == trace_payload
