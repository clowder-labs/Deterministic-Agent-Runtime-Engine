"""STM 组件贡献者：序列化/恢复短期记忆消息列表."""

from __future__ import annotations

from dare_framework.checkpoint.interfaces import ICheckpointContributor
from dare_framework.checkpoint.types import CheckpointContext, STM
from dare_framework.context.types import Message


class StmContributor(ICheckpointContributor):
    @property
    def component_key(self) -> str:
        return STM

    def serialize(self, ctx: CheckpointContext) -> list[dict]:
        if ctx.context is None:
            return []
        messages = ctx.context.stm_get()
        return [
            {
                "role": m.role,
                "content": m.content,
                "name": m.name,
                "metadata": dict(m.metadata),
            }
            for m in messages
        ]

    def deserialize_and_apply(self, payload: list, ctx: CheckpointContext) -> None:
        if ctx.context is None:
            return
        ctx.context.stm_clear()
        for item in payload or []:
            if isinstance(item, dict):
                msg = Message(
                    role=item.get("role", "user"),
                    content=item.get("content", ""),
                    name=item.get("name"),
                    metadata=dict(item.get("metadata") or {}),
                )
                ctx.context.stm_add(msg)
