"""In-memory checkpoint store."""

from __future__ import annotations

from dare_framework.checkpoint.interfaces import ICheckpointStore
from dare_framework.checkpoint.types import CheckpointPayload


class MemoryCheckpointStore(ICheckpointStore):
    """内存存储，进程内有效."""

    def __init__(self) -> None:
        self._store: dict[str, CheckpointPayload] = {}

    def put(self, checkpoint_id: str, payload: CheckpointPayload) -> None:
        self._store[checkpoint_id] = dict(payload)

    def get(self, checkpoint_id: str) -> CheckpointPayload | None:
        return dict(self._store[checkpoint_id]) if checkpoint_id in self._store else None

    def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._store:
            del self._store[checkpoint_id]
            return True
        return False
