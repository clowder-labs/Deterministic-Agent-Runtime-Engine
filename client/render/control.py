"""Renderer for structured control-stdin responses."""

from __future__ import annotations

import json
import time
from typing import Any


class ControlStdinRenderer:
    """Emit versioned responses for stdin-driven host control."""

    schema_version = "client-control-stdin.v1"

    def emit(
        self,
        *,
        request_id: str,
        ok: bool,
        result: Any = None,
        error: Any = None,
    ) -> None:
        print(
            json.dumps(
                {
                    "schema_version": self.schema_version,
                    "ts": time.time(),
                    "id": request_id,
                    "ok": ok,
                    "result": result,
                    "error": error,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
