## Context

PR #113 已明确把“文档治理哲学互学”拆分为独立变更执行。本仓库已具备文档先行 SOP、gap/TODO 台账与 OpenSpec 流程，但“同一变更的全链路上下文”仍分散在 `openspec/changes/`、`docs/design/`、`docs/todos/`、PR 评论中，缺少统一聚合入口和可机器检索的挂接元数据。

本设计将“可重建性”扩展为“可重建 + 可追溯”：不仅要求文档可重建系统，还要求任何治理变更都能被快速追踪其设计声明、执行计划、证据与归档状态，并能通过 CI 自动识别流程缺口。

## Goals / Non-Goals

**Goals:**
- 为治理类变更建立统一聚合模型（single aggregation entry per change）。
- 定义 frontmatter 最小合约并约束跨文档挂接字段。
- 建立活跃索引与归档迁移规则，避免上下文散落。
- 将关键门禁（文档更新、gap/TODO 映射、聚合完整性）转化为可自动检查的 checkpoint。

**Non-Goals:**
- 不引入新的运行时能力或 agent 执行路径变更。
- 不重构历史所有文档，只做“新治理变更必须遵循”的前向约束与最小回填。
- 不改变 OpenSpec CLI 本身行为，仅在仓库侧补流程与检查。

## Decisions

### Decision 1: 聚合主键使用 OpenSpec change-id，而非新增 Feature 编号体系
- 方案 A（采用）：聚合文档以 `openspec change-id` 为主键，例如 `docs/features/<change-id>.md`。
- 方案 B（不采用）：引入独立 `Fxxx` 编号并维护映射表。
- 理由：A 与现有治理流程天然对齐，避免并行编号体系导致维护成本上升。

### Decision 2: frontmatter 合约采用“最小必填 + 可扩展字段”
- 必填：`feature_ids`（或 `change_ids`）、`topics`、`doc_kind`、`created`。
- 可选：`debt_ids`、`related_specs`、`status`。
- 理由：先保证可检索与可追踪，再逐步扩展，避免一次性要求过重。

### Decision 3: 治理 checkpoint 以 CI 脚本为主，人工评审为补充
- 方案 A（采用）：新增/增强脚本校验，CI gate 强制执行；人工仅处理脚本无法判定的语义问题。
- 方案 B（不采用）：完全依赖 review checklist。
- 理由：流程门禁需要“默认可执行且可复现”，否则会被长期稀释。

### Decision 4: 采用“前向生效 + 最小回填”迁移策略
- 新变更从生效日起必须满足聚合 + frontmatter + checkpoint。
- 历史文档按活跃优先级回填，不阻塞本次治理基线落地。

## Risks / Trade-offs

- [Risk] 新增 frontmatter 与聚合文档带来短期编辑负担  
  → Mitigation: 提供模板与示例，脚本错误信息给出修复建议。

- [Risk] 规则过严影响迭代效率  
  → Mitigation: 先启用 warning 模式验证一轮，再切换到 hard gate。

- [Risk] 历史文档不完整导致初期误报  
  → Mitigation: 校验范围优先限制到“本次变更触达文件 + 新增文件”。

## Migration Plan

1. 新增治理聚合模板与 frontmatter 合约文档。
2. 在 `docs/guides` 与 `docs/design` 回写执行顺序与术语。
3. 增加 CI 检查脚本（聚合入口、frontmatter、gap/TODO 映射）。
4. 选取一个活跃变更做样例回填，验证流程可用性。
5. 将 checkpoint 从 warning 提升为阻断门禁并更新贡献指南。

回滚策略：若新 gate 导致大量误报，可临时降级为 warning，同时保留文档合约与聚合模板，不回退语义规范。

## Open Questions

- frontmatter 字段名统一使用 `feature_ids` 还是 `change_ids` 作为主字段？
- 聚合文档目录命名是否固定为 `docs/features/`，还是放入 `docs/governance/`？
- 是否在后续迭代增加自动生成聚合骨架（由脚本从 OpenSpec change 初始化）？
