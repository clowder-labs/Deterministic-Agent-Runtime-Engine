## Context

当前测试覆盖面较广，但缺少围绕 P0 不变量的统一门禁视图。多个能力分散在 unit/integration 中，发布时难以快速回答“P0 是否仍成立”。为避免后续变更破坏核心承诺，需要建立集中、可追踪、可阻断的 conformance gate。

## Goals / Non-Goals

**Goals:**
- 建立聚焦 P0 的测试与 CI 门禁机制。
- 让关键不变量失败时可以一键阻断合并。
- 输出可读的失败分类，缩短回归定位时间。
- 将门禁与 OpenSpec 任务闭环对齐，支持持续验收。

**Non-Goals:**
- 本次不构建通用性能基准平台。
- 本次不覆盖所有业务场景，只聚焦 P0 主链路。
- 本次不替代现有全量测试，仅新增一层发布级硬门槛。

## Decisions

### Decision 1: 定义 P0 门禁维度
- Security Gate: 工具调用前 trust/policy 决策必须生效。
- Execution Gate: `step_driven` 执行路径必须可用且可验证。
- Audit Gate: 默认 event log 的 hash-chain/replay 必须通过。
- 理由：与 P0 范围一一对应，避免门禁目标漂移。

### Decision 2: 门禁优先使用集成用例 + 关键单测
- 集成用例覆盖跨域链路，关键单测覆盖稳定契约。
- CI `p0-gate` 仅跑必要集合，避免过重导致反馈过慢。
- 理由：平衡信号质量与执行效率。

### Decision 3: 门禁失败标准化输出
- 统一失败标签（`SECURITY_REGRESSION`、`STEP_EXEC_REGRESSION`、`AUDIT_CHAIN_REGRESSION`）。
- 在 CI summary 输出失败类型、触发用例、建议排查模块。
- 理由：减少“测试红了但不知先看哪里”的协作摩擦。

### Decision 4: 与发布流程绑定
- `p0-gate` 设为 required check，main 分支合并必须通过。
- 版本发布前重复执行并归档结果。
- 理由：把质量要求前置到提交阶段。

## Risks / Trade-offs

- [Risk] 新门禁增加 CI 时长，影响迭代速度。  
  → Mitigation: 只纳入高价值用例，并按变更范围优化触发策略。
- [Risk] 门禁过严导致早期开发体验下降。  
  → Mitigation: 允许 feature branch 软失败，主分支强制。
- [Risk] 用例维护成本上升。  
  → Mitigation: 每个 P0 change 同步维护对应门禁用例，避免债务累积。

## Migration Plan

1. 先定义 `p0-gate` 用例清单与失败标签规范。
2. 补齐缺失的集成用例与关键单测。
3. 在 CI 增加 `p0-gate` job（先观察模式，后切 required）。
4. 观察两周稳定性后升级为主分支强制门禁。
5. 发布流程增加门禁结果归档。

Rollback:
- 将 `p0-gate` 从 required 降级为非阻断检查，同时保留报告输出。

## Open Questions

- 是否需要把 P0 指标写入 machine-readable 报告（如 JSON）供 dashboard 消费？
- `p0-gate` 是否按路径变更做选择性触发，还是始终全量执行？
- 对于 flaky 用例，是否设立临时 quarantine 机制与期限？
