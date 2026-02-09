"""session_state / session_context 组件贡献者：序列化会话状态与上下文."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from dare_framework.checkpoint.interfaces import ICheckpointContributor
from dare_framework.checkpoint.types import (
    CheckpointContext,
    SESSION_CONTEXT,
    SESSION_STATE,
)


def _serialize_session_state(state: Any) -> dict | None:
    if state is None:
        return None
    try:
        return asdict(state)
    except Exception:
        return {"task_id": getattr(state, "task_id", None), "run_id": getattr(state, "run_id", None)}


def _serialize_session_context(sc: Any) -> dict | None:
    if sc is None:
        return None
    try:
        d = asdict(sc)
        # Config 可能不可 asdict，简化为 None 或跳过
        if "config" in d and d["config"] is not None:
            try:
                d["config"] = asdict(d["config"])
            except Exception:
                d["config"] = None
        return d
    except Exception:
        return {"session_id": getattr(sc, "session_id", None), "task_id": getattr(sc, "task_id", None)}


class SessionStateContributor(ICheckpointContributor):
    @property
    def component_key(self) -> str:
        return SESSION_STATE

    def serialize(self, ctx: CheckpointContext) -> dict | None:
        return _serialize_session_state(ctx.session_state)

    def deserialize_and_apply(self, payload: Any, ctx: CheckpointContext) -> None:
        if payload is None or ctx.session_state is None:
            return
        # 最小恢复：仅恢复可写字段，避免重建复杂嵌套类型
        if isinstance(payload, dict):
            if "current_milestone_idx" in payload:
                ctx.session_state.current_milestone_idx = payload["current_milestone_idx"]


class SessionContextContributor(ICheckpointContributor):
    @property
    def component_key(self) -> str:
        return SESSION_CONTEXT

    def serialize(self, ctx: CheckpointContext) -> dict | None:
        return _serialize_session_context(ctx.session_context)

    def deserialize_and_apply(self, payload: Any, ctx: CheckpointContext) -> None:
        # SessionContext 多为只读/构造时确定，此处仅做序列化留存；恢复不改写
        if payload is None or ctx.session_context is None:
            return
