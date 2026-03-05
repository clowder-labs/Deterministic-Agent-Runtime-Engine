"""checkpoint - AgentState checkpoint 门面（当前仅包含 STM）。

当前版本：
- 定义通用 `AgentState` 抽象（目前只有 `stm` 字段）；
- 提供可配置后端的 agent_state checkpoint 管理器（默认使用文件持久化 backend="file"）；

后续可以在不破坏接口形状的前提下，为 `AgentState` 增加更多字段。
"""

from dare_framework.checkpoint.kernel import (
    AgentState,
    AgentStateCheckpoint,
    AgentStateCheckpointer,
    CheckpointId,
)

__all__ = [
    "CheckpointId",
    "AgentState",
    "AgentStateCheckpoint",
    "AgentStateCheckpointer",
]
