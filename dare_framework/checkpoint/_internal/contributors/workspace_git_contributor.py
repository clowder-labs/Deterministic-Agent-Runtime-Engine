"""workspace_files 组件贡献者：通过 Agent 裸仓 Git 保存/恢复工作区文件."""

from __future__ import annotations

from dare_framework.checkpoint._internal.git_runner import (
    add_and_commit,
    checkout_commit,
    ensure_agent_repo,
)
from dare_framework.checkpoint.interfaces import ICheckpointContributor
from dare_framework.checkpoint.types import CheckpointContext, WORKSPACE_FILES


class WorkspaceGitContributor(ICheckpointContributor):
    """使用 .dare/agent.git + --work-tree 管理工程根；payload 仅存 git_commit."""

    @property
    def component_key(self) -> str:
        return WORKSPACE_FILES

    def serialize(self, ctx: CheckpointContext) -> dict:
        """执行 add+commit，返回 {"git_commit": "<sha>"}."""
        workspace_dir = ctx.workspace_dir or "."
        # checkpoint_id 在 SaveRestore 层才生成，这里用占位；commit message 仅做标识
        sha = add_and_commit(workspace_dir, "DARE Checkpoint: workspace snapshot")
        return {"git_commit": sha}

    def deserialize_and_apply(self, payload: dict, ctx: CheckpointContext) -> None:
        """根据 git_commit checkout 工作区."""
        if not payload or "git_commit" not in payload:
            return
        workspace_dir = ctx.workspace_dir or "."
        ensure_agent_repo(workspace_dir)
        checkout_commit(workspace_dir, payload["git_commit"])
