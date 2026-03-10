"""checkpoint: agent_state checkpoint manager（当前仅包含 STM）.

设计目标：
- 抽象出一个可扩展的 `AgentState`，用于保存/恢复 Agent 运行时状态；
- 当前实现里 `AgentState` 只包含 STM（短期记忆），后续可以逐步加入 session_state、
  plan_state、workspace 快照等，而不破坏 checkpoint 的接口形状；
- 仍然保持 API 轻量：内存实现 + `save` / `restore` / `delete` / `list`，
  方便在任务过程中自动保存，并支持 `/resume <id>` 回滚到指定状态。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List
from uuid import uuid4

from dare_framework.context.types import AttachmentRef, Message, MessageKind, MessageMark, MessageRole

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext


CheckpointId = str

# 单用户/单目录下最多保留的 checkpoint 数量，超出时删除最老的
CHECKPOINT_LIMIT = 100


@dataclass(frozen=True)
class AgentState:
    """Agent 的运行时状态快照（当前仅包含 STM，预留扩展位）。"""

    stm: List["Message"]
    # 未来可扩展字段示例（目前暂不启用，避免破坏最小实现）:
    # session_state: Any | None = None
    # plan_state: Any | None = None
    # workspace_diff: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentStateCheckpoint:
    """单个 agent_state checkpoint 快照.

    Attributes:
        checkpoint_id: 唯一 ID（十六进制字符串），用于 `/resume <id>` 等外部控制命令。
        created_at: 创建时间（time.time() 秒）。
        state: 当时的 AgentState 快照（当前仅 STM）。
    """

    checkpoint_id: CheckpointId
    created_at: float
    state: AgentState
    # 简短描述当时的现场（例如最近一条用户指令），用于 CLI/UI 展示与选择。
    summary: str = ""


class AgentStateCheckpointManager:
    """管理 agent_state 的 checkpoint 管理器，支持多种持久化后端。

    后端通过构造参数指定：
    - backend="memory"：只在进程内内存中保存 checkpoint；
    - backend="file"(默认)：保存到指定目录的 JSON 文件，支持跨进程/重启恢复；
    - backend="sqlite" 等其它值暂未实现，传入会抛出 ValueError。

    典型用法::

        mgr = AgentStateCheckpointManager()

        cp_id = mgr.save(ctx)
        ...
        mgr.restore(cp_id, ctx)
    """

    def __init__(
        self,
        *,
        backend: str = "file",
        checkpoint_dir: str | Path = ".dare/agent_state_checkpoints",
        max_checkpoints: int = CHECKPOINT_LIMIT,
    ) -> None:
        normalized = (backend or "memory").strip().lower()
        if normalized not in {"memory", "file"}:
            raise ValueError(f"unsupported agent_state checkpoint backend: {backend!r}")
        if max_checkpoints < 1:
            raise ValueError("max_checkpoints must be >= 1")
        self._backend = normalized
        self._max_checkpoints = max_checkpoints
        self._checkpoints: Dict[CheckpointId, AgentStateCheckpoint] = {}
        if self._backend == "file":
            self._checkpoint_dir = Path(checkpoint_dir)
            self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公共 API：save / restore / delete / get / list / clear
    # ------------------------------------------------------------------

    def save(self, ctx: "IContext") -> CheckpointId:
        """保存当前 agent_state（当前仅 STM）状态，返回 checkpoint_id."""

        checkpoint_id: CheckpointId = uuid4().hex[:16]
        state = AgentState(stm=list(ctx.stm_get()))
        checkpoint = AgentStateCheckpoint(
            checkpoint_id=checkpoint_id,
            created_at=time.time(),
            state=state,
            summary=_summarize_state(state),
        )

        if self._backend == "memory":
            self._checkpoints[checkpoint_id] = checkpoint
        else:  # file backend
            self._write_checkpoint(checkpoint)
        self._trim_to_limit()
        return checkpoint_id

    def restore(self, checkpoint_id: CheckpointId, ctx: "IContext") -> None:
        """将 agent_state（当前仅 STM）回滚到指定 checkpoint_id.

        Raises:
            KeyError: 当 checkpoint_id 不存在时。
        """

        checkpoint = self.get(checkpoint_id)
        if checkpoint is None:
            raise KeyError(f"AgentState checkpoint not found: {checkpoint_id!r}")

        ctx.stm_clear()
        for msg in checkpoint.state.stm:
            ctx.stm_add(msg)

    def delete(self, checkpoint_id: CheckpointId) -> bool:
        """删除指定 checkpoint，返回是否存在过."""

        if self._backend == "memory":
            return self._checkpoints.pop(checkpoint_id, None) is not None

        path = self._path_for(checkpoint_id)
        if not path.exists():
            return False
        try:
            path.unlink()
        except OSError:
            return False
        return True

    def get(self, checkpoint_id: CheckpointId) -> AgentStateCheckpoint | None:
        """获取指定 checkpoint 元信息（不修改运行中上下文）."""

        if self._backend == "memory":
            return self._checkpoints.get(checkpoint_id)

        path = self._path_for(checkpoint_id)
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            return None
        return self._deserialize_checkpoint(data)

    def list(self) -> list[AgentStateCheckpoint]:
        """按创建时间升序返回所有 checkpoint."""

        if self._backend == "memory":
            return sorted(self._checkpoints.values(), key=lambda cp: cp.created_at)

        checkpoints: list[AgentStateCheckpoint] = []
        for file in sorted(self._checkpoint_dir.glob("*.json")):
            try:
                raw = file.read_text(encoding="utf-8")
                data = json.loads(raw)
            except Exception:
                continue
            checkpoint = self._deserialize_checkpoint(data)
            if checkpoint is not None:
                checkpoints.append(checkpoint)
        return sorted(checkpoints, key=lambda cp: cp.created_at)

    def clear(self) -> None:
        """清空所有 checkpoint（不修改当前 STM）."""

        if self._backend == "memory":
            self._checkpoints.clear()
            return

        for file in self._checkpoint_dir.glob("*.json"):
            try:
                file.unlink()
            except OSError:
                continue

    def _trim_to_limit(self) -> None:
        """保留最近 _max_checkpoints 条，超出则按 created_at 删除最老的。"""
        all_cp = self.list()
        if len(all_cp) <= self._max_checkpoints:
            return
        to_remove = all_cp[: len(all_cp) - self._max_checkpoints]
        for cp in to_remove:
            self.delete(cp.checkpoint_id)

    # ------------------------------------------------------------------
    # 文件后端工具方法（backend == "file" 时使用）
    # ------------------------------------------------------------------

    def _path_for(self, checkpoint_id: CheckpointId) -> Path:
        return self._checkpoint_dir / f"{checkpoint_id}.json"

    def _write_checkpoint(self, checkpoint: AgentStateCheckpoint) -> None:
        payload = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "created_at": checkpoint.created_at,
            "state": self._serialize_state(checkpoint.state),
            "summary": checkpoint.summary,
        }
        path = self._path_for(checkpoint.checkpoint_id)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def _serialize_state(state: AgentState) -> dict[str, Any]:
        """将 AgentState 序列化为 JSON 友好的 dict."""

        return {
            "stm": [
                {
                    "role": m.role.value if isinstance(m.role, MessageRole) else str(m.role),
                    "kind": m.kind.value if isinstance(m.kind, MessageKind) else str(m.kind),
                    "text": m.text,
                    "attachments": [
                        {
                            "kind": attachment.kind.value,
                            "uri": attachment.uri,
                            "mime_type": attachment.mime_type,
                            "filename": attachment.filename,
                            "metadata": dict(attachment.metadata),
                        }
                        for attachment in m.attachments
                    ],
                    "data": dict(m.data) if isinstance(m.data, dict) else None,
                    "name": m.name,
                    "metadata": dict(getattr(m, "metadata", {}) or {}),
                    "mark": m.mark.value if isinstance(m.mark, MessageMark) else str(m.mark),
                    "id": m.id,
                }
                for m in state.stm
            ],
        }

    @staticmethod
    def _deserialize_state(data: dict[str, Any]) -> AgentState:
        """从 dict 反序列化为 AgentState."""

        stm_items = data.get("stm") or []
        messages: list[Message] = []
        for item in stm_items:
            if not isinstance(item, dict):
                continue
            msg = Message(
                role=item.get("role", "user"),
                kind=item.get("kind", MessageKind.CHAT.value),
                text=item.get("text", item.get("content", "")),
                attachments=AttachmentRef.coerce_many(item.get("attachments")),
                data=dict(item.get("data")) if isinstance(item.get("data"), dict) else None,
                name=item.get("name"),
                metadata=dict(item.get("metadata") or {}),
                mark=item.get("mark", MessageMark.TEMPORARY.value),
                id=item.get("id"),
            )
            messages.append(msg)
        return AgentState(stm=messages)

    def _deserialize_checkpoint(self, data: dict[str, Any]) -> AgentStateCheckpoint | None:
        checkpoint_id = data.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id:
            return None
        created_at_raw = data.get("created_at", 0.0)
        try:
            created_at = float(created_at_raw)
        except (TypeError, ValueError):
            created_at = 0.0
        state_data = data.get("state")
        if not isinstance(state_data, dict):
            state = AgentState(stm=[])
        else:
            state = self._deserialize_state(state_data)
        raw_summary = data.get("summary")
        summary = str(raw_summary).strip() if isinstance(raw_summary, str) else ""
        if not summary:
            summary = _summarize_state(state)
        return AgentStateCheckpoint(
            checkpoint_id=checkpoint_id,
            created_at=created_at,
            state=state,
            summary=summary,
        )


def _summarize_state(state: AgentState) -> str:
    """为 AgentState 生成简短描述（当前基于 STM 消息）。

    优先策略：
    - 最近一条 role == "user" 且有内容的消息；
    - 否则最后一条消息；
    - 否则 "(无对话内容)"。
    最长保留 60 个字符，多余部分使用 "..." 截断。
    """

    messages = getattr(state, "stm", []) or []
    summary = ""
    # 优先最近 user 消息
    for m in reversed(messages):
        role = getattr(m, "role", "")
        content = getattr(m, "text", None)
        if not isinstance(content, str):
            content = getattr(m, "content", "") or ""
        if role == "user" and content.strip():
            summary = content.strip()
            break
    # 退而求其次：最后一条消息
    if not summary and messages:
        last_text = getattr(messages[-1], "text", None)
        if not isinstance(last_text, str):
            last_text = getattr(messages[-1], "content", "") or ""
        summary = last_text.strip()
    if not summary:
        summary = "(无对话内容)"
    if len(summary) > 60:
        summary = summary[:60] + "..."
    return summary


class AgentStateCheckpointer:
    """agent_state checkpoint 的单一入口，支持多后端与便捷构造。

    构造参数：
    - backend: "memory" 仅进程内存；"file" 持久化到目录（默认）。
    - checkpoint_dir: 存储目录（file 后端时使用）；与 user_dir 二选一。
    - user_dir: 用户目录，未传 checkpoint_dir 时使用 user_dir/.dare/agent_state_checkpoints；
      两者都不传时使用 Path.home()/.dare/agent_state_checkpoints。

    示例::

        checkpointer = AgentStateCheckpointer(user_dir=str(Path.home()))
        cp_id = checkpointer.save(ctx)
        checkpointer.restore(cp_id, ctx)
        checkpointer.list(print_to_stdout=True)
    """

    def __init__(
        self,
        *,
        backend: str = "file",
        checkpoint_dir: str | Path | None = None,
        user_dir: str | Path | None = None,
    ) -> None:
        normalized = (backend or "file").strip().lower()
        if normalized not in {"memory", "file"}:
            raise ValueError(f"unsupported agent_state checkpoint backend: {backend!r}")
        self._backend = normalized
        if checkpoint_dir is not None:
            self._dir = Path(checkpoint_dir)
        elif user_dir is not None:
            self._dir = Path(user_dir) / ".dare" / "agent_state_checkpoints"
        else:
            self._dir = Path.home() / ".dare" / "agent_state_checkpoints"
        self._mgr = AgentStateCheckpointManager(
            backend=normalized,
            checkpoint_dir=self._dir,
        )

    @property
    def checkpoint_dir(self) -> Path:
        """当前 checkpoint 存储目录（file 后端时有效）。"""
        return self._dir

    def save(self, ctx: "IContext") -> CheckpointId:
        """保存当前 agent_state（当前仅 STM），返回 checkpoint_id。"""
        return self._mgr.save(ctx)

    def restore(self, checkpoint_id: CheckpointId, ctx: "IContext") -> None:
        """将 agent_state 回滚到指定 checkpoint_id。"""
        self._mgr.restore(checkpoint_id, ctx)

    def get(self, checkpoint_id: CheckpointId) -> AgentStateCheckpoint | None:
        """获取指定 checkpoint 元信息（不修改运行中上下文）。"""
        return self._mgr.get(checkpoint_id)

    def delete(self, checkpoint_id: CheckpointId) -> bool:
        """删除指定 checkpoint，返回是否曾存在。"""
        return self._mgr.delete(checkpoint_id)

    def list(self, *, print_to_stdout: bool = False) -> list[AgentStateCheckpoint]:
        """返回所有 checkpoint；print_to_stdout=True 时同时打印到 stdout。"""
        checkpoints = self._mgr.list()
        if print_to_stdout:
            if not checkpoints:
                print("[checkpoint] 当前没有可恢复的 checkpoint。", flush=True)
            else:
                print("\n[checkpoint] 可用 checkpoint（最新在下方）:", flush=True)
                for idx, cp in enumerate(checkpoints, 1):
                    ts = datetime.fromtimestamp(cp.created_at).strftime("%Y-%m-%d %H:%M:%S")
                    summary = (cp.summary or "").strip() or "(无对话内容)"
                    print(f"  [{idx}] {cp.checkpoint_id} | {ts} | {summary}", flush=True)
        return checkpoints

    def clear(self) -> None:
        """清空所有 checkpoint（不修改当前 STM）。"""
        self._mgr.clear()


__all__ = [
    "CheckpointId",
    "AgentState",
    "AgentStateCheckpoint",
    "AgentStateCheckpointer",
]
