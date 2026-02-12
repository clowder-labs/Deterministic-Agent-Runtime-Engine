"""Checkpoint domain facade."""

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
from dare_framework.checkpoint.factory import create_default_save_restore
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
