## Why

项目已将 EventLog 定义为状态外化与审计复验的核心，但 canonical `event` domain 目前仅有接口，缺少默认实现。没有开箱可用的事件链，很多“可审计/可回放”能力只能停留在设计层，无法成为默认运行保障。

## What Changes

- 在 `dare_framework/event` 域提供默认 `IEventLog` 实现（sqlite 持久化 + hash-chain）。
- 提供 `append/query/replay/verify_chain` 的完整实现，并冻结最小事件表结构。
- 在 `DareAgentBuilder` 增加默认 event log 装配能力（可配置路径/开关）。
- 统一事件 payload 序列化策略，保证 query/replay 的稳定行为。
- 将现有遗留/跳过的 event 测试迁移到 canonical 实现并加入回归门禁。

## Capabilities

### New Capabilities
- `default-event-log`: 默认可用的审计日志实现，支持 hash-chain 校验与最小 replay。

### Modified Capabilities
- `core-runtime`: 从“可选 event log 注入”升级为“可默认装配事件链能力”。
- `session-loop`: 会话与里程碑关键事件写入路径收敛到 canonical event domain。
- `observability`: 与 trace bridge 对齐，确保事件链与观测链可共同追踪。

## Impact

- Affected code:
  - `dare_framework/event/_internal/sqlite_event_log.py` (new)
  - `dare_framework/event/defaults.py` (new)
  - `dare_framework/event/__init__.py`
  - `dare_framework/agent/builder.py`
  - `dare_framework/config/types.py`
  - `tests/unit/test_event_log.py`
  - `tests/unit/test_five_layer_agent.py`
  - `tests/integration/test_example_agent_flow.py`
- Data/ops impact:
  - 默认产生本地 sqlite 事件文件，需明确路径与清理策略。
  - 事件结构变更后需要保持向后兼容读取（若存在旧数据）。
