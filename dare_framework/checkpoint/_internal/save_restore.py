"""默认 Checkpoint 保存/恢复实现：按 scope 调用各 Contributor 并读写 Store."""

from __future__ import annotations

from uuid import uuid4

from dare_framework.checkpoint.interfaces import (
    ICheckpointContributor,
    ICheckpointSaveRestore,
    ICheckpointStore,
)
from dare_framework.checkpoint.types import (
    CheckpointContext,
    CheckpointPayload,
    CheckpointScope,
)


class DefaultCheckpointSaveRestore(ICheckpointSaveRestore):
    def __init__(
        self,
        store: ICheckpointStore,
        contributors: list[ICheckpointContributor],
    ) -> None:
        self._store = store
        self._contributors = {c.component_key: c for c in contributors}

    def save(
        self,
        scope: CheckpointScope,
        ctx: CheckpointContext,
    ) -> str:
        payload: CheckpointPayload = {}
        for key in scope.keys_for_save():
            contrib = self._contributors.get(key)
            if contrib is None:
                continue
            try:
                payload[key] = contrib.serialize(ctx)
            except Exception as e:
                raise RuntimeError(f"Checkpoint save failed for component {key!r}") from e
        checkpoint_id = uuid4().hex[:16]
        self._store.put(checkpoint_id, payload)
        return checkpoint_id

    def restore(
        self,
        checkpoint_id: str,
        scope: CheckpointScope,
        ctx: CheckpointContext,
    ) -> None:
        payload = self._store.get(checkpoint_id)
        if payload is None:
            raise LookupError(f"Checkpoint not found: {checkpoint_id!r}")
        for key in scope.keys_for_restore():
            if key not in payload:
                continue
            contrib = self._contributors.get(key)
            if contrib is None:
                continue
            try:
                contrib.deserialize_and_apply(payload[key], ctx)
            except Exception as e:
                raise RuntimeError(f"Checkpoint restore failed for component {key!r}") from e
