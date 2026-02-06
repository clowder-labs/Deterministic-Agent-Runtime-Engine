"""Checkpoint domain types: scope, component keys, payload, runtime context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 组件键：与 PLAN.md 一致
STM = "stm"
SESSION_STATE = "session_state"
SESSION_CONTEXT = "session_context"
CONFIG = "config"
PLAN_STATE = "plan_state"
BUDGET = "budget"
WORKSPACE_FILES = "workspace_files"

COMPONENT_KEYS = (
    STM,
    SESSION_STATE,
    SESSION_CONTEXT,
    CONFIG,
    PLAN_STATE,
    BUDGET,
    WORKSPACE_FILES,
)


@dataclass
class ComponentScope:
    """单个组件在 save/restore 中是否参与."""

    include_in_save: bool = True
    include_in_restore: bool = True


@dataclass
class CheckpointScope:
    """本次 save/restore 涉及哪些组件及各自开关."""

    components: dict[str, ComponentScope] = field(default_factory=dict)

    def include_in_save(self, key: str) -> bool:
        c = self.components.get(key)
        return c.include_in_save if c else False

    def include_in_restore(self, key: str) -> bool:
        c = self.components.get(key)
        return c.include_in_restore if c else False

    def keys_for_save(self) -> list[str]:
        return [k for k in self.components if self.include_in_save(k)]

    def keys_for_restore(self) -> list[str]:
        return [k for k in self.components if self.include_in_restore(k)]


class ScopePresets:
    """预设的 CheckpointScope（每次返回新实例，避免共享可变状态）."""

    @staticmethod
    def all() -> CheckpointScope:
        return CheckpointScope(
            components={k: ComponentScope(True, True) for k in COMPONENT_KEYS}
        )

    @staticmethod
    def stm_only() -> CheckpointScope:
        return CheckpointScope(components={STM: ComponentScope(True, True)})

    @staticmethod
    def stm_and_session() -> CheckpointScope:
        return CheckpointScope(
            components={
                STM: ComponentScope(True, True),
                SESSION_STATE: ComponentScope(True, True),
                SESSION_CONTEXT: ComponentScope(True, True),
            }
        )

    @staticmethod
    def stm_and_workspace() -> CheckpointScope:
        return CheckpointScope(
            components={
                STM: ComponentScope(True, True),
                WORKSPACE_FILES: ComponentScope(True, True),
            }
        )


# Checkpoint  payload：各组件键 -> 可序列化 dict（JSON 友好）
CheckpointPayload = dict[str, Any]


@dataclass
class CheckpointContext:
    """保存/恢复时传入的运行时上下文，供各 Contributor 读写."""

    # 工程根目录，Git --work-tree 的基准
    workspace_dir: str = "."
    # 以下为可选引用，Contributor 按需使用
    context: Any = None  # IContext
    session_state: Any = None  # SessionState | None
    session_context: Any = None  # SessionContext | None
    config: Any = None  # Config | None
