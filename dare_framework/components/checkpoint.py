from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..core.interfaces import ICheckpoint
from ..core.models import RuntimeSnapshot, RuntimeState


class FileCheckpoint(ICheckpoint):
    def __init__(self, path: str = ".dare/checkpoints") -> None:
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)

    async def save(self, snapshot: RuntimeSnapshot) -> str:
        checkpoint_id = snapshot.saved_at.strftime("%Y%m%d%H%M%S")
        file_path = self._path / f"{checkpoint_id}.json"
        payload = asdict(snapshot)
        payload["state"] = snapshot.state.value
        payload["saved_at"] = snapshot.saved_at.isoformat()
        file_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return checkpoint_id

    async def load(self, checkpoint_id: str) -> RuntimeSnapshot:
        file_path = self._path / f"{checkpoint_id}.json"
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return RuntimeSnapshot(
            state=RuntimeState(payload["state"]),
            task_id=payload["task_id"],
            milestone_id=payload.get("milestone_id"),
            saved_at=_parse_timestamp(payload["saved_at"]),
        )


def _parse_timestamp(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
