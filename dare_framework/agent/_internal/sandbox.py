"""Plan attempt sandbox for STM state isolation.

Provides snapshot/rollback capability to ensure failed plan attempts
do not pollute milestone context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.context.types import Message


class DefaultPlanAttemptSandbox:
    """Default implementation of IPlanAttemptSandbox using STM snapshots.

    Creates in-memory snapshots of the STM message list and supports
    rollback to restore previous state on plan failure.

    Example:
        sandbox = DefaultPlanAttemptSandbox()
        snapshot_id = sandbox.create_snapshot(ctx)

        try:
            # Execute plan attempt
            ...
        except ValidationError:
            sandbox.rollback(ctx, snapshot_id)
        else:
            sandbox.commit(snapshot_id)
    """

    def __init__(self) -> None:
        """Initialize sandbox with empty snapshot store."""
        self._snapshots: dict[str, list[Message]] = {}

    def create_snapshot(self, ctx: IContext) -> str:
        """Create a snapshot of the current STM state.

        Args:
            ctx: Context containing STM to snapshot.

        Returns:
            Unique snapshot_id for later rollback or commit.
        """
        snapshot_id = uuid4().hex[:8]
        # Copy current STM messages using stm_get()
        self._snapshots[snapshot_id] = list(ctx.stm_get())
        return snapshot_id

    def rollback(self, ctx: IContext, snapshot_id: str) -> None:
        """Rollback STM to a previous snapshot state.

        Args:
            ctx: Context containing STM to restore.
            snapshot_id: ID from create_snapshot().

        Raises:
            KeyError: If snapshot_id is not found.
        """
        if snapshot_id not in self._snapshots:
            raise KeyError(f"Snapshot {snapshot_id} not found")

        # Restore STM from snapshot using public API
        snapshot_messages = self._snapshots[snapshot_id]
        ctx.stm_clear()  # Clear current STM
        for msg in snapshot_messages:
            ctx.stm_add(msg)  # Re-add snapshot messages

        # Discard this snapshot after rollback
        del self._snapshots[snapshot_id]

    def commit(self, snapshot_id: str) -> None:
        """Discard a snapshot, keeping current state.

        Args:
            snapshot_id: ID of snapshot to discard.
        """
        self._snapshots.pop(snapshot_id, None)

    def clear_all(self) -> None:
        """Clear all stored snapshots."""
        self._snapshots.clear()

    @property
    def snapshot_count(self) -> int:
        """Number of active snapshots."""
        return len(self._snapshots)


__all__ = ["DefaultPlanAttemptSandbox"]
