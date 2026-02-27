## Context

当前 `dare_framework/event/kernel.py` 定义了完整接口，但没有默认实现，导致运行时常依赖外部注入或 mock。仓库中存在历史 event log 路径与跳过测试，增加了维护成本，也削弱了“默认可审计”的产品承诺。

## Goals / Non-Goals

**Goals:**
- 提供 canonical `SQLiteEventLog` 并满足 `IEventLog` 全部方法。
- 建立稳定 hash-chain 计算口径与篡改检测能力。
- 支持最小 replay 快照输出，满足 P0 可复验需求。
- 在 builder 中提供默认装配，降低使用门槛。

**Non-Goals:**
- 本次不做分布式日志复制与多节点一致性。
- 本次不实现复杂索引优化或冷热分层存储。
- 本次不实现全文检索型 query 能力。

## Decisions

### Decision 1: sqlite 作为默认本地持久化后端
- 采用单文件 sqlite 存储，兼顾可移植性与开发门槛。
- 事件表包含 `event_id`、`event_type`、`payload_json`、`timestamp`、`prev_hash`、`hash`。
- 理由：足够支撑 P0 的审计链与 replay，同时易于测试和部署。

### Decision 2: hash-chain 计算口径固定
- `hash = H(event_type + payload_json + timestamp + prev_hash)`。
- `payload_json` 使用稳定排序序列化，避免同语义不同字节导致链不一致。
- 理由：保证跨进程复验可重复。

### Decision 3: builder 默认按配置自动装配
- 若用户未显式 `with_event_log()`，builder 根据 config 决定是否创建默认 sqlite event log。
- 默认路径放在 workspace 下（例如 `.dare/events.db`），并支持覆盖。
- 理由：把“可审计”从可选增强变为默认基础能力。

### Decision 4: legacy 路径迁移策略
- 在 canonical tests 中替换 legacy import；保留短期兼容层但不再新增依赖。
- 理由：减少双实现漂移与测试噪声。

## Risks / Trade-offs

- [Risk] sqlite 文件增长可能影响长期运行性能。  
  → Mitigation: 先提供基础归档/轮转参数，后续再做分层存储。
- [Risk] hash 口径一旦变更会影响旧链复验。  
  → Mitigation: 在 schema 中记录 hash_version，并通过迁移脚本兼容旧数据。
- [Risk] 默认启用 event log 可能引入 I/O 开销。  
  → Mitigation: 提供开关，并保证 append 路径轻量化。

## Migration Plan

1. 新增 `SQLiteEventLog` 与默认工厂，完成 `IEventLog` 四方法实现。
2. 在 builder 接入默认 event log 装配与配置解析。
3. 打通 observability trace bridge 与默认实现兼容性测试。
4. 将 `tests/unit/test_event_log.py` 从 skip 状态迁移到 canonical 验证。
5. 增加 replay/hash-chain 集成测试并纳入 CI。

Rollback:
- 通过配置关闭默认 event log 装配，或回退到显式注入模式。

## Open Questions

- 是否需要在 P0 就支持事件数据加密（at-rest）？
- `replay` 的最小快照字段是否要覆盖 budget/context 摘要？
- 默认事件保留周期和清理策略由框架还是宿主应用负责？
