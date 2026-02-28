"""SQLite-backed default event log implementation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event, RuntimeSnapshot


class SQLiteEventLog(IEventLog):
    """Canonical SQLite-backed implementation of ``IEventLog``.

    The storage is append-only and maintains a hash-chain using
    ``prev_hash`` -> ``event_hash`` for tamper detection.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
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
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_id ON events(event_id)")
        self._conn.commit()

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        event = Event(event_type=event_type, payload=dict(payload or {}))
        payload_json = self._payload_to_json(event.payload)
        timestamp_iso = event.timestamp.isoformat()

        async with self._lock:
            prev_hash = self._last_event_hash()
            event_hash = self._compute_event_hash(
                event_id=event.event_id,
                event_type=event.event_type,
                timestamp_iso=timestamp_iso,
                payload_json=payload_json,
                prev_hash=prev_hash,
            )
            self._conn.execute(
                (
                    "INSERT INTO events (event_id, event_type, payload_json, timestamp_iso, prev_hash, event_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (event.event_id, event.event_type, payload_json, timestamp_iso, prev_hash, event_hash),
            )
            self._conn.commit()
            return event.event_id

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Event]:
        bounded_limit = max(0, int(limit))
        if bounded_limit == 0:
            return []

        clauses: list[str] = []
        params: list[Any] = []
        event_filter = dict(filter or {})

        event_type = event_filter.get("event_type")
        if isinstance(event_type, str) and event_type:
            clauses.append("event_type = ?")
            params.append(event_type)

        event_id = event_filter.get("event_id")
        if isinstance(event_id, str) and event_id:
            clauses.append("event_id = ?")
            params.append(event_id)

        sql = (
            "SELECT event_id, event_type, payload_json, timestamp_iso, prev_hash, event_hash "
            "FROM events"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY seq ASC LIMIT ?"
        params.append(bounded_limit)

        async with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        async with self._lock:
            anchor = self._conn.execute(
                "SELECT seq FROM events WHERE event_id = ?",
                (from_event_id,),
            ).fetchone()
            if anchor is None:
                raise ValueError(f"from_event_id not found: {from_event_id}")
            rows = self._conn.execute(
                (
                    "SELECT event_id, event_type, payload_json, timestamp_iso, prev_hash, event_hash "
                    "FROM events WHERE seq >= ? ORDER BY seq ASC"
                ),
                (int(anchor["seq"]),),
            ).fetchall()

        events = [self._row_to_event(row) for row in rows]
        return RuntimeSnapshot(from_event_id=from_event_id, events=events)

    async def verify_chain(self) -> bool:
        async with self._lock:
            rows = self._conn.execute(
                (
                    "SELECT event_id, event_type, payload_json, timestamp_iso, prev_hash, event_hash "
                    "FROM events ORDER BY seq ASC"
                )
            ).fetchall()

        previous_hash: str | None = None
        for row in rows:
            row_prev_hash = row["prev_hash"]
            row_event_hash = row["event_hash"]
            if row_prev_hash != previous_hash:
                return False

            expected_hash = self._compute_event_hash(
                event_id=row["event_id"],
                event_type=row["event_type"],
                timestamp_iso=row["timestamp_iso"],
                payload_json=row["payload_json"],
                prev_hash=row_prev_hash,
            )
            if row_event_hash != expected_hash:
                return False
            previous_hash = row_event_hash

        return True

    def close(self) -> None:
        """Close the underlying sqlite connection."""
        self._conn.close()

    def _last_event_hash(self) -> str | None:
        row = self._conn.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return row["event_hash"]

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        timestamp = datetime.fromisoformat(row["timestamp_iso"])
        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        return Event(
            event_id=row["event_id"],
            event_type=row["event_type"],
            payload=payload,
            timestamp=timestamp,
            prev_hash=row["prev_hash"],
            event_hash=row["event_hash"],
        )

    def _payload_to_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _compute_event_hash(
        self,
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

DefaultEventLog = SQLiteEventLog

__all__ = ["SQLiteEventLog", "DefaultEventLog"]
