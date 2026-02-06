"""封装 Agent 裸仓 Git 操作：--git-dir=.dare/agent.git --work-tree=<workspace_dir>."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


# Agent 仓相对工作区根目录的路径
AGENT_GIT_DIR = ".dare/agent.git"

# excludesfile 内容：排除用户 .git 和 .dare，避免循环跟踪
EXCLUDES_CONTENT = """# DARE checkpoint agent repo: do not track user .git or self
.git/
.dare/
"""


def _run_git(
    workspace_dir: str,
    args: list[str],
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """在 workspace_dir 下执行 git，使用 Agent 裸仓与当前工作区."""
    env = os.environ.copy()
    env["GIT_DIR"] = str(Path(workspace_dir).resolve() / AGENT_GIT_DIR)
    env["GIT_WORK_TREE"] = str(Path(workspace_dir).resolve())
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["git"] + args,
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def ensure_agent_repo(workspace_dir: str) -> None:
    """若不存在则创建 .dare/agent.git 裸仓并配置 excludesfile."""
    root = Path(workspace_dir).resolve()
    git_dir = root / AGENT_GIT_DIR
    if (git_dir / "HEAD").exists():
        return
    git_dir.mkdir(parents=True, exist_ok=True)
    # init --bare
    r = subprocess.run(
        ["git", "init", "--bare"],
        cwd=str(root),
        env={**os.environ, "GIT_DIR": str(git_dir)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    r.check_returncode()
    # excludesfile
    excludes_path = git_dir / "info" / "exclude"
    excludes_path.parent.mkdir(parents=True, exist_ok=True)
    excludes_path.write_text(EXCLUDES_CONTENT, encoding="utf-8")
    # 可选：配置 user 以便 commit
    _run_git(workspace_dir, ["config", "user.name", "DARE Checkpoint"])
    _run_git(workspace_dir, ["config", "user.email", "checkpoint@dare.local"])


def add_and_commit(workspace_dir: str, message: str) -> str:
    """add -A 并 commit，返回 commit SHA（40 字符）。无变更时返回当前 HEAD."""
    ensure_agent_repo(workspace_dir)
    _run_git(workspace_dir, ["add", "-A"])
    r = _run_git(workspace_dir, ["commit", "-m", message])
    if r.returncode != 0 and "nothing to commit" in (r.stderr or ""):
        # 无变更，当前状态已与上次 commit 一致，返回当前 HEAD
        pass
    elif r.returncode != 0:
        r.check_returncode()
    rev = _run_git(workspace_dir, ["rev-parse", "HEAD"])
    if rev.returncode != 0:
        # 可能尚无任何 commit，做一次空提交
        _run_git(workspace_dir, ["commit", "--allow-empty", "-m", message])
        rev = _run_git(workspace_dir, ["rev-parse", "HEAD"])
    rev.check_returncode()
    return rev.stdout.strip()[:40]


def checkout_commit(workspace_dir: str, commit_sha: str) -> None:
    """强制将工作区恢复到指定 commit（不移动 HEAD 分支，只覆盖工作区文件）。"""
    r = _run_git(workspace_dir, ["checkout", "-f", commit_sha, "--", "."])
    r.check_returncode()


def clean_untracked(workspace_dir: str) -> None:
    """删除未跟踪的文件/目录，排除 .git 和 .dare."""
    _run_git(workspace_dir, ["clean", "-fdq", "-e", ".git", "-e", ".dare"])
