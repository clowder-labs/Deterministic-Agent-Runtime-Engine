"""SQLite-backed raw data storage implementation."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from dare_framework.knowledge._internal.rawdata_knowledge.storage.interfaces import (
    IRawDataStore,
    RawRecord,
)


class SQLiteRawDataStorage(IRawDataStore):
    """SQLite-backed raw data store (single file, persistent)."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize with database file path.

        Args:
            db_path: Path to SQLite file (e.g. "./rawdata.db"). Created if missing.
        """
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_records (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_content ON raw_records(content)"
        )
        self._conn.commit()

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        if not content:
            raise ValueError("Content cannot be empty")
        rid = str(uuid.uuid4())
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO raw_records (id, content, metadata) VALUES (?, ?, ?)",
            (rid, content, meta_json),
        )
        self._conn.commit()
        return rid

    def get(self, record_id: str) -> RawRecord | None:
        row = self._conn.execute(
            "SELECT id, content, metadata FROM raw_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        return RawRecord(id=row["id"], content=row["content"], metadata=meta)

    def remove(self, record_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM raw_records WHERE id = ?", (record_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def clear(self) -> None:
        self._conn.execute("DELETE FROM raw_records")
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM raw_records").fetchone()
        return row["n"] if row else 0

    def search(self, query: str = "", top_k: int = 100) -> list[RawRecord]:
        if not query:
            rows = self._conn.execute(
                "SELECT id, content, metadata FROM raw_records LIMIT ?", (top_k,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, content, metadata FROM raw_records WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", top_k),
            ).fetchall()
        out = []
        for row in rows:
            meta = json.loads(row["metadata"]) if row["metadata"] else {}
            out.append(RawRecord(id=row["id"], content=row["content"], metadata=meta))
        return out

    def list_all(self) -> list[RawRecord]:
        rows = self._conn.execute(
            "SELECT id, content, metadata FROM raw_records"
        ).fetchall()
        out = []
        for row in rows:
            meta = json.loads(row["metadata"]) if row["metadata"] else {}
            out.append(RawRecord(id=row["id"], content=row["content"], metadata=meta))
        return out

    def close(self) -> None:
        """Close the database connection. Optional; connection is held for lifetime."""
        self._conn.close()

    def __enter__(self) -> SQLiteRawDataStorage:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = ["SQLiteRawDataStorage"]
