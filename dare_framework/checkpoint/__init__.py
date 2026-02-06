# Checkpoint: 现场保存与恢复能力
# 完整计划见 PLAN.md

from dare_framework.checkpoint.interfaces import (
    ICheckpointContributor,
    ICheckpointSaveRestore,
    ICheckpointStore,
)
from dare_framework.checkpoint.types import (
    CheckpointContext,
    CheckpointScope,
    ScopePresets,
)
from dare_framework.checkpoint._internal.memory_store import MemoryCheckpointStore
from dare_framework.checkpoint._internal.save_restore import DefaultCheckpointSaveRestore
from dare_framework.checkpoint._internal.contributors.stm_contributor import StmContributor
from dare_framework.checkpoint._internal.contributors.workspace_git_contributor import (
    WorkspaceGitContributor,
)
from dare_framework.checkpoint._internal.contributors.session_contributor import (
    SessionStateContributor,
    SessionContextContributor,
)


def create_default_save_restore(
    store: ICheckpointStore | None = None,
    *,
    include_session_contributors: bool = True,
) -> ICheckpointSaveRestore:
    """创建默认的 SaveRestore：STM + workspace_files，可选 session_state/session_context."""
    if store is None:
        store = MemoryCheckpointStore()
    contributors: list[ICheckpointContributor] = [
        StmContributor(),
        WorkspaceGitContributor(),
    ]
    if include_session_contributors:
        contributors.extend([SessionStateContributor(), SessionContextContributor()])
    return DefaultCheckpointSaveRestore(store=store, contributors=contributors)


__all__ = [
    "ICheckpointContributor",
    "ICheckpointSaveRestore",
    "ICheckpointStore",
    "CheckpointContext",
    "CheckpointScope",
    "ScopePresets",
    "MemoryCheckpointStore",
    "DefaultCheckpointSaveRestore",
    "create_default_save_restore",
]
