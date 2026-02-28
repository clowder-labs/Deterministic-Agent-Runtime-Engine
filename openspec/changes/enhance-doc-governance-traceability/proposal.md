## Why

PR #113 中已经确认“文档治理哲学互学”应拆到独立 OpenSpec 变更执行。当前仓库虽有文档先行约束，但缺少以“Feature/Change 生命周期”为中心的统一聚合入口、结构化挂接元数据与可自动验证的治理 checkpoint，导致跨文档追溯和长期维护成本偏高。

## What Changes

- 引入“按变更聚合”的文档治理基线：每个治理变更都有单一聚合文档入口，统一挂接相关设计、讨论、TODO 与证据。
- 统一 `docs/` 目录结构分层（标准/设计/治理/特性聚合/分析TODO/临时/归档），并明确各类型文档放置规则。
- 定义并落地文档 `frontmatter` 最小字段合约（如 `feature_ids` / `topics` / `doc_kind` / `created`），用于机器可检索追溯。
- 增加活跃治理索引与状态迁移规则（active -> archived），避免长期任务上下文分散。
- 把关键治理门禁转化为可验证 checkpoint（脚本/CI 检查），覆盖：文档更新、gap/TODO 关联、聚合入口完整性。
- 将文档先行 SOP 的关键阶段（kickoff / execution / completion / verification）显式 skill 化，并明确至少拆分为“文档管理 skill + 工作流 skill”两类职责。
- 增加协作双模式声明：OpenSpec 默认模式 + 无 OpenSpec 时的 TODO-driven 回退模式与迁移规则。
- 在现有 `docs/guides/*` 与 `docs/design/*` 中回写统一术语与执行顺序，确保与 OpenSpec 工作流一致。

## Capabilities

### New Capabilities
- `documentation-lifecycle-traceability`: 定义治理变更的聚合入口、frontmatter 挂接规范、活跃索引与归档迁移闭环。

### Modified Capabilities
- `design-reconstructability-governance`: 扩展为“可重建 + 可追溯”双目标，并要求治理 checkpoint 具备机器可验证性。

## Impact

- Affected docs:
  - `docs/guides/Documentation_First_Development_SOP.md`
  - `docs/guides/Development_Constraints.md`
  - `docs/design/Design_Reconstructability_Traceability_Matrix.md`
  - 新增治理聚合与索引文档（路径将在 design/tasks 中定版）
- Affected automation/checks:
  - `scripts/ci/check_design_doc_drift.sh`（或新增 companion check）
  - CI gate 组合中的文档治理校验步骤
- Affected skills/docs:
  - `.codex/skills/documentation-management/SKILL.md`
  - `.codex/skills/development-workflow/SKILL.md`
  - skill 与 checkpoint 的映射文档（路径将在 design/tasks 中定版）
- API/runtime impact:
  - 无运行时接口变更（non-breaking）
