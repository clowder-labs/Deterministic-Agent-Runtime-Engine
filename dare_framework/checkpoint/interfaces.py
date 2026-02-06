"""Checkpoint domain interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dare_framework.checkpoint.types import (
    CheckpointContext,
    CheckpointPayload,
    CheckpointScope,
)


class ICheckpointStore(ABC):
    """Checkpoint 存储抽象：put/get/delete."""

    @abstractmethod
    def put(self, checkpoint_id: str, payload: CheckpointPayload) -> None:
        """写入 checkpoint payload."""
        ...

    @abstractmethod
    def get(self, checkpoint_id: str) -> CheckpointPayload | None:
        """读取 checkpoint payload，不存在返回 None."""
        ...

    @abstractmethod
    def delete(self, checkpoint_id: str) -> bool:
        """删除指定 checkpoint，返回是否曾存在."""
        ...


class ICheckpointContributor(ABC):
    """单个组件的序列化/反序列化贡献者."""

    @property
    @abstractmethod
    def component_key(self) -> str:
        """组件键，与 types.COMPONENT_KEYS 一致."""
        ...

    def serialize(self, ctx: CheckpointContext) -> Any:
        """从运行时采集该组件数据，返回可序列化结构（可 JSON 化）."""
        ...

    def deserialize_and_apply(
        self, payload: Any, ctx: CheckpointContext
    ) -> None:
        """从 payload 写回该组件到运行时."""
        ...


class ICheckpointSaveRestore(ABC):
    """现场保存与恢复入口."""

    @abstractmethod
    def save(
        self,
        scope: CheckpointScope,
        ctx: CheckpointContext,
    ) -> str:
        """按 scope 采集状态并保存，返回 checkpoint_id."""
        ...

    @abstractmethod
    def restore(
        self,
        checkpoint_id: str,
        scope: CheckpointScope,
        ctx: CheckpointContext,
    ) -> None:
        """从 checkpoint_id 按 scope 恢复状态."""
        ...
