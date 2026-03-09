# 文档先行开发 SOP（强制执行）

> 适用范围：本仓库所有开发活动（AI Agent + Human），包含 Bug 修复、新增 Feature、重构。  
> 生效目标：确保即使代码丢失，也可基于文档重建系统。

## 1. 强制原则

1. Agent 开发必须遵循 `docs/guides/` 约束，禁止绕开规范直接改代码。
2. 所有实现以 `docs/design/` 为准，`docs/design/` 维护“全量、最新、可执行”的设计事实。
3. 设计文档必须可重建实现，必须明确：
   - 总体架构
   - 核心流程
   - 数据结构
   - 关键接口
   - 异常与错误处理
4. 任何 Bug/Feature/Refactor，必须先判断是否为设计约束不清或缺失；是则先补文档。
5. 开发闭环必须是：全局分析 -> 总体 TODO 主清单 -> 认领声明 -> docs 更新 -> 按 TODO 切片建立 OpenSpec / execution board -> docs-only intent PR 合入 -> 实现 -> TODO/证据回写 -> 文档归档。
6. `docs/**` 是全量事实源；`openspec/**` 仅是执行过程记录。OpenSpec 结果必须回写到 `docs/**`，禁止只留在 OpenSpec。

## 2. 产物规范（必须）

- 设计文档：`docs/design/**`
- 特性聚合文档：`docs/features/<change-id>.md`（状态单一真相源）
- 设计质量标准：`docs/design/Design_Doc_Minimum_Standard.md`
- 差异分析：`docs/todos/YYYY-MM-DD_<topic>_design_code_gap_analysis.md`
- 总体 TODO 主清单：`docs/todos/YYYY-MM-DD_<topic>_master_todo.md`（可映射多个 OpenSpec change 切片）
- 执行清单：`docs/todos/YYYY-MM-DD_<topic>_design_code_gap_todo.md`
- OpenSpec 变更记录（过程）：`openspec/changes/<change-id>/{proposal.md,design.md,tasks.md}`
- 归档产物：分析文档、TODO 文档在完成后标记 `done/archived`，并补证据链接。
- 可重建追踪矩阵：`docs/design/Design_Reconstructability_Traceability_Matrix.md`
- 重建执行 SOP：`docs/guides/Design_Reconstruction_SOP.md`
- 文档治理模型：`docs/governance/Documentation_Management_Model.md`
- Evidence Truth 策略：`docs/guides/Evidence_Truth_Implementation_Strategy.md`

## 3. 标准流程（一步不可省）

### Step 0: 任务归类
- 输入必须归入 `bug` / `feature` / `refactor` 之一。
- 明确影响范围：模块、接口、数据结构、流程、错误处理。

### Step 1: 全局分析（先于执行）
- 对任务做完整分析：现状、目标、影响范围、风险、依赖、边界。
- 若属于结构性改造（接口/schema/protocol/state model/workflow 边界调整），必须在分析阶段完成 scope freeze：明确 `in scope`、`out of scope`、`deferred`。
- 产出或更新 gap 分析文档，确保每条分析有文档/代码证据锚点。
- 大改动必须先得到“可拆分切片”的分析结论，禁止直接进入执行。

### Step 2: 生成总体 TODO 主清单
- 基于分析文档生成总体 TODO 主清单，覆盖完整目标范围。
- 每条 TODO 必须标记切片边界（可独立执行、可独立验证、可独立回滚）。
- 总体 TODO 必须支持映射多个 OpenSpec change（一个大特性通常对应多个 change）。
- 每条进入执行态的 TODO 切片必须可映射到唯一 `Claim Ledger` scope。

### Step 2.5: 认领声明（冲突规避，强制）
- 在开始实现前，必须先在对应 TODO 文档写入 `Claim Ledger` 认领声明。
- 最少字段：`Claim ID`、`TODO Scope`、`Owner`、`Status`、`Declared At`、`Expires At`、`OpenSpec Change`。
- 同一 TODO scope 在同一时刻只允许一个 `planned/active` 认领。
- 认领只声明“这一块范围由谁推进”，不替代 active change 内部的 work package 协作板。

### Step 3: 先更新 docs（作为 OpenSpec 输入）
- 在执行前先更新 `docs/design/**` 与相关治理文档，形成当前基线。
- 对接口/schema/protocol 改造，docs 更新前必须先列出入口清单：public API、transport、client helper、examples、tests、adapter、持久化、文档/guide。
- TODO 与 design 是 OpenSpec proposal/design 的输入，不是执行后补写。
- 若缺文档，先补文档，不允许“先写代码再补文档”。
- 文档结构必须满足最小标准（见 `Design_Doc_Minimum_Standard.md`）。

### Step 4: 按 TODO 切片进入 OpenSpec
- 从总体 TODO 中选择一个最小切片，创建/更新一个 OpenSpec change。
- 每个 change 必须声明其消费的 TODO 子集与验收边界。
- 一个 change 只处理一个切片；多切片并行时使用多个 change-id。
- 若该切片存在多人并行、共享接口、或需要 Gate 冻结，则必须创建/更新 `docs/todos/YYYY-MM-DD_<change-id>_execution_todos.md`。

### Step 4.5: 合入 docs-only intent PR（实现前门禁）
- 在进入代码实现前，必须提交一个只包含治理文档的 `spec-sync / intent PR` 并先合入 `main`。
- 该 PR 至少包含：
  - `Claim Ledger` 更新；
  - 本轮切片对应的 docs/OpenSpec artifacts；
  - 若需要多人协作，则包含 execution board 骨架与 Gate/Touch Scope 定义。
- `intent PR` 禁止夹带实现代码；其目的仅是把意图、边界、冻结点写入共享基线。
- 机器校验门禁：`./scripts/ci/check_governance_intent_gate.sh` 在实现路径变更时会强制校验“已更新 governed feature doc + Intent PR 已合并”。

### Step 5: 按 OpenSpec 切片逐项执行修复
- 每个切片在 OpenSpec 中落地为可追踪 proposal/design/tasks。
- 推荐节奏：一条 TODO（切片子项） -> OpenSpec task -> 实现 -> 验证 -> 回写状态。
- 禁止一次性跨多个高风险 TODO 混改。
- 未完成 `intent PR` 合入前，不得开始实现代码或提交实现 PR。
- 若 `check_governance_intent_gate.sh` 失败，必须先修复 feature doc / intent 链接状态，再继续实现提交。

### Step 6: 验证与回写
- 每次切片修复后必须同步更新：
  - 对应 `docs/design/**` 文档
  - 对应 `docs/todos/*_master_todo.md` 与 `docs/todos/*_todo.md` 状态与证据
  - 对应 OpenSpec `tasks.md` 状态
- 验证至少覆盖：测试、接口契约、错误分支、文档一致性。
- `docs/features/<change-id>.md`（或 fallback 的 `<topic-slug>.md`）必须按 Evidence Truth 模板回写：
  - `Commands`
  - `Results`
  - `Contract Delta`（schema/error semantics/retry，均可为变更或 none/n.a + reason）
  - `Golden Cases`（新增/更新文件名）
  - `Regression Summary`（runner 输出摘要）
  - `Observability and Failure Localization`（start/tool_call/end/fail + locator 字段）
  - `Structured Review Report`
  - `Behavior Verification`（happy path + error branch）
  - `Risks and Rollback`
  - `Review and Merge Gate Links`
- 必须执行并通过：`./scripts/ci/check_governance_evidence_truth.sh`。
- 对实现路径变更 PR，必须执行并通过：`./scripts/ci/check_governance_intent_gate.sh`。
- 对结构性改造，Step 6 结束前必须执行一次全局回扫：确认代码、测试、examples、active docs、规范文档、归档索引中不存在旧接口/旧协议/旧术语残留。

### Step 7: 归档
- 总体 TODO 全部切片完成后：
  - 将分析文档和 TODO 文档标记为 `archived` 或迁移到历史区块
  - 在 `docs/todos/README.md` 更新索引
  - 对每个已完成 OpenSpec change 执行 archive（如适用）

### Gap 分析最小字段（适用于 Step 1）
- 生成分析文档时，最少包含以下列：
  - `Gap ID`
  - `设计声明（Design Claim）`
  - `代码现状（Code Evidence）`
  - `影响评估（Impact）`
  - `建议动作（Action）`
  - `优先级（P0/P1/P2/P3）`
- 每条 Gap 必须带具体文件证据（文档路径 + 代码路径）。

## 4. 强制门禁（DoD）

- 未完成 Step 1（全局分析）不得进入切片执行。
- 未完成 Step 2（总体 TODO）不得创建 OpenSpec change。
- 未完成 Step 2.5（认领声明）不得进入 Step 4/Step 5。
- 未完成 Step 3（docs 更新）不得进入代码提交。
- 未完成 Step 4（切片映射）不得开始批量修复。
- 未完成 Step 4.5（docs-only intent PR 合入）不得开始代码实现。
- 未通过 `./scripts/ci/check_governance_intent_gate.sh` 不得合入实现 PR。
- 未完成 Step 6（验证+回写）不得标记切片完成。
- 未完成 Step 7（归档）不得关闭该轮治理任务。

## 5. 紧急修复例外（仅限生产止血）

- 允许先做最小止血改动，但必须在 24 小时内补齐：
  1. 设计文档修订
  2. gap 分析
  3. TODO 与 OpenSpec 追踪
- 超时未补齐，视为流程违规。

## 6. 周期性全量评审与证据归档（防腐化）

1. 评审节奏：至少每两周执行一次全量设计评审（Architecture + 全部模块 README）。
2. 评审输出：必须产出当轮 gap 分析与 TODO 清单，并在 `project_overall_todos.md` 回写状态。
3. 证据归档规则：
   - 归档路径统一使用日期前缀（`YYYY-MM-DD-...`）。
   - 归档条目必须包含对应 OpenSpec change 路径与验证证据。
4. 若连续两轮发现同类文档漂移，必须新增自动化校验并接入 CI。

## 7. 协作模式（必须显式声明）

### Mode A: OpenSpec 模式（默认）

适用于 OpenSpec 可用场景，执行顺序如下：
1. 先完成分析 + 总体 TODO 主清单 + docs 基线更新。
2. 在 TODO `Claim Ledger` 先声明认领（scope/owner/expires/change-id）。
3. 从总体 TODO 选择一个切片，建立/选择 `openspec/changes/<change-id>/`。
4. 创建或更新 `docs/features/<change-id>.md`，登记该切片的 proposal/design/specs/tasks 链接。
5. 若切片需要多人并行、共享接口冻结或联调顺序控制，则创建/更新对应 execution board。
6. 提交 docs-only `intent PR` 并先合入 `main`。
7. 基于最新 `main` 开始实现，按 OpenSpec tasks 执行该切片，并回写证据到 feature 聚合文档与 TODO 文档。
8. 重复步骤 2-7，直到总体 TODO 主清单清空。
9. 完成后执行 verify + archive，并迁移聚合文档到 `docs/features/archive/`。
10. 确认最终可读性以 `docs/**` 为准：架构/流程/接口变更已在 docs 中可独立理解，OpenSpec 仅保留追踪链接。

### Mode B: 无 OpenSpec 回退（TODO-driven）

仅在 OpenSpec 不可用（工具/环境受限）时使用：
1. 先完成分析 + 总体 TODO 主清单 + docs 基线更新。
2. 在 TODO `Claim Ledger` 先声明认领（scope/owner/expires）。
3. 创建 `docs/features/<topic-slug>.md`，并在 frontmatter 声明 `mode: todo_fallback` 与 `topic_slug`。
4. 若该切片需要多人并行或共享接口冻结，则创建/更新 execution board。
5. 提交 docs-only `intent PR` 并先合入 `main`。
6. 以 TODO 清单推进并持续回写 evidence（不阻塞于 OpenSpec 工具可用性）。
7. OpenSpec 可用后，按 TODO 切片补迁移：将 fallback 资产映射到一个或多个新的 `openspec/changes/<change-id>/` 并记录迁移证据。

## 8. SOP Skill 化（必须）

SOP 关键阶段必须有可调用技能承载，并保持 checkpoint 与 skill 映射一致：
- kickoff
- execution-sync
- verification
- review-merge-gate
- completion-archive

当前双技能分工：
- 文档管理技能（类型/路径/frontmatter/归档）：
  - `.codex/skills/documentation-management/SKILL.md`
- 开发流程技能（模式选择/checkpoint/证据回写）：
  - `.codex/skills/development-workflow/SKILL.md`
- 经验沉淀技能（仅在用户明确要求总结经验/刷新流程时触发）：
  - `.codex/skills/retrospective-process-hardening/SKILL.md`

经验沉淀技能的职责边界：
- 抽取已完成工作的 lessons learned
- 将候选经验分类为 `update-sop` / `update-existing-skill` / `create-new-skill` / `do-not-codify`
- 仅将经过分类筛选的高价值通用规则回写到 SOP/skill
- 不得把 domain-specific 设计结论直接写成通用流程规则

若 SOP 与 skill 行为不一致，以规范文档更新 + skill 同步更新为同一任务，禁止只改其一。
