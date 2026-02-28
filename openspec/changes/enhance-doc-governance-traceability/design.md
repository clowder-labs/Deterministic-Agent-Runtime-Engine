## Context

PR #113 已明确把“文档治理哲学互学”拆分为独立变更执行。本仓库已具备文档先行 SOP、gap/TODO 台账与 OpenSpec 流程，但“同一变更的全链路上下文”仍分散在 `openspec/changes/`、`docs/design/`、`docs/todos/`、PR 评论中，缺少统一聚合入口和可机器检索的挂接元数据。

本设计将“可重建性”扩展为“可重建 + 可追溯”：不仅要求文档可重建系统，还要求任何治理变更都能被快速追踪其设计声明、执行计划、证据与归档状态，并能通过 CI 自动识别流程缺口。

## Goals / Non-Goals

**Goals:**
- 统一文档目录分层与各类型文档放置规则，减少“同类文档多位置散落”。
- 为治理类变更建立统一聚合模型（single aggregation entry per change）。
- 定义 frontmatter 最小合约并约束跨文档挂接字段。
- 建立活跃索引与归档迁移规则，避免上下文散落。
- 将关键门禁（文档更新、gap/TODO 映射、聚合完整性）转化为可自动检查的 checkpoint。
- 将文档治理 SOP 关键阶段 skill 化，使治理执行不仅“有规范”，且“可调用、可复用、可审计”。
- 明确 OpenSpec 与 TODO fallback 的协作边界及迁移策略。

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

### Decision 5: 关键治理步骤由 Skill 承载执行语义
- 方案 A（采用）：采用双技能架构，至少包含 `documentation-management`（管理）与 `documentation-workflow`（流程）两类职责，并维护“checkpoint -> skill”映射文档；保留 `documentation-lifecycle-governance` 作为兼容入口。
- 方案 B（不采用）：只在 SOP 文档里描述步骤，不提供可调用 skill。
- 理由：仅文档约束容易漂移；双技能拆分可降低职责耦合并增强复用，skill 化可以将治理流程变成可执行协议并支持自动审计。

### Decision 6: 采用双协作模式但以 OpenSpec 为默认主干
- 方案 A（采用）：OpenSpec 作为默认执行模式；无 OpenSpec 时允许 TODO-driven fallback，并要求后续迁移回 OpenSpec。
- 方案 B（不采用）：仅允许 OpenSpec，不提供回退。
- 理由：在工具受限场景下需要保留最小可执行治理流程，但必须可回收进入统一主干。

## Risks / Trade-offs

- [Risk] 新增 frontmatter 与聚合文档带来短期编辑负担  
  → Mitigation: 提供模板与示例，脚本错误信息给出修复建议。

- [Risk] 规则过严影响迭代效率  
  → Mitigation: 先启用 warning 模式验证一轮，再切换到 hard gate。

- [Risk] 历史文档不完整导致初期误报  
  → Mitigation: 校验范围优先限制到“本次变更触达文件 + 新增文件”。

- [Risk] skill 规范与 SOP 文档双处维护导致不一致  
  → Mitigation: 强制维护 checkpoint-skill 映射源文件，并在 CI 中校验映射完整性。

- [Risk] 双协作模式可能产生长期并行流程  
  → Mitigation: fallback 文档必须带迁移计划与截至条件，且在 OpenSpec 可用后强制迁移。

## Migration Plan

1. 新增治理聚合模板与 frontmatter 合约文档。
2. 明确 `docs/` 目录分层与文档类型放置规则，并同步导航文档。
3. 在 `docs/guides` 与 `docs/design` 回写执行顺序与术语（含 OpenSpec/fallback 协作规则）。
4. 增加/更新治理 skills，并建立 checkpoint 到 skill 的映射文档。
5. 增加 CI 检查脚本（聚合入口、frontmatter、gap/TODO 映射、skill 映射完整性）。
6. 选取一个活跃变更做样例回填，验证流程可用性。
7. 将 checkpoint 从 warning 提升为阻断门禁并更新贡献指南。

回滚策略：若新 gate 导致大量误报，可临时降级为 warning，同时保留文档合约与聚合模板，不回退语义规范。

## Open Questions

- frontmatter 字段名统一使用 `feature_ids` 还是 `change_ids` 作为主字段？
- 聚合文档目录命名是否固定为 `docs/features/`，还是放入 `docs/governance/`？
- 是否在后续迭代增加自动生成聚合骨架（由脚本从 OpenSpec change 初始化）？
- 是否在下一迭代提供脚手架命令自动生成 `documentation-management` / `documentation-workflow` 的最小执行模板？
