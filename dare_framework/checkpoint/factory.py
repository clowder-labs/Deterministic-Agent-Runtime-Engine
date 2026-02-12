"""Checkpoint factory helpers."""

from __future__ import annotations

from dare_framework.checkpoint.interfaces import (
    ICheckpointContributor,
    ICheckpointSaveRestore,
    ICheckpointStore,
)
from dare_framework.checkpoint._internal.contributors.session_contributor import (
    SessionContextContributor,
    SessionStateContributor,
)
from dare_framework.checkpoint._internal.contributors.stm_contributor import StmContributor
from dare_framework.checkpoint._internal.contributors.workspace_git_contributor import (
    WorkspaceGitContributor,
)
from dare_framework.checkpoint._internal.memory_store import MemoryCheckpointStore
from dare_framework.checkpoint._internal.save_restore import DefaultCheckpointSaveRestore


def create_default_save_restore(
    store: ICheckpointStore | None = None,
    *,
    include_session_contributors: bool = True,
) -> ICheckpointSaveRestore:
    """Create default save/restore with STM and workspace contributors."""

    checkpoint_store = store if store is not None else MemoryCheckpointStore()
    contributors: list[ICheckpointContributor] = [
        StmContributor(),
        WorkspaceGitContributor(),
    ]
    if include_session_contributors:
        contributors.extend([SessionStateContributor(), SessionContextContributor()])
    return DefaultCheckpointSaveRestore(store=checkpoint_store, contributors=contributors)


__all__ = ["create_default_save_restore"]
