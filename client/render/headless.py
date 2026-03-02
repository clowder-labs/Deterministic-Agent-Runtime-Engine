"""Renderer for host-orchestrated headless event envelopes."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4


class HeadlessRenderer:
    """Emit versioned event frames for host orchestration."""

    schema_version = "client-headless-event-envelope.v1"

    def __init__(self) -> None:
        default_id = uuid4().hex
        self._session_id = default_id
        self._run_id = default_id
        self._seq = 0

    def set_context(self, *, session_id: str | None = None, run_id: str | None = None) -> None:
        if session_id:
            self._session_id = session_id
        if run_id:
            self._run_id = run_id

    def emit(self, event: str, payload: Any) -> None:
        self._seq += 1
        print(
            json.dumps(
                {
                    "schema_version": self.schema_version,
                    "ts": time.time(),
                    "session_id": self._session_id,
                    "run_id": self._run_id,
                    "seq": self._seq,
                    "event": event,
                    "data": payload,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
