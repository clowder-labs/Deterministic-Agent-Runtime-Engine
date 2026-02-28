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
5. 开发闭环必须是：文档更新 -> gap 分析 -> TODO 清单 -> OpenSpec 执行 -> TODO 回写 -> 文档归档。

## 2. 产物规范（必须）

- 设计文档：`docs/design/**`
- 特性聚合文档：`docs/features/<change-id>.md`（状态单一真相源）
- 设计质量标准：`docs/design/Design_Doc_Minimum_Standard.md`
- 差异分析：`docs/todos/YYYY-MM-DD_<topic>_design_code_gap_analysis.md`
- 执行清单：`docs/todos/YYYY-MM-DD_<topic>_design_code_gap_todo.md`
- OpenSpec 变更：`openspec/changes/<change-id>/{proposal.md,design.md,tasks.md}`
- 归档产物：分析文档、TODO 文档在完成后标记 `done/archived`，并补证据链接。
- 可重建追踪矩阵：`docs/design/Design_Reconstructability_Traceability_Matrix.md`
- 重建执行 SOP：`docs/guides/Design_Reconstruction_SOP.md`
- 文档治理模型：`docs/governance/Documentation_Management_Model.md`

## 3. 标准流程（一步不可省）

### Step 0: 任务归类
- 输入必须归入 `bug` / `feature` / `refactor` 之一。
- 明确影响范围：模块、接口、数据结构、流程、错误处理。

### Step 1: 文档先行更新
- 先更新 `docs/design/` 对应文档，再进入代码实现。
- 若缺文档，先补文档，不允许“先写代码再补文档”。
- 文档结构必须满足最小标准（见 `Design_Doc_Minimum_Standard.md`）。

### Step 2: 设计-实现 Gap 分析
- 生成分析文档，最少包含以下列：
  - `Gap ID`
  - `设计声明（Design Claim）`
  - `代码现状（Code Evidence）`
  - `影响评估（Impact）`
  - `建议动作（Action）`
  - `优先级（P0/P1/P2/P3）`
- 每条 Gap 必须带具体文件证据（文档路径 + 代码路径）。

### Step 3: 从 Gap 生成 TODO 清单
- 基于 Gap 文档生成 TODO（禁止拍脑袋列 TODO）。
- 每条 TODO 必须映射至少一个 Gap ID。
- 每条 TODO 必须包含：
  - `ID`, `Priority`, `Status`, `Owner`, `Related Gap`, `Evidence`, `Last Updated`

### Step 4: 按 OpenSpec 逐项执行修复
- 每个 TODO 项在 OpenSpec 中落地为可追踪任务。
- 推荐节奏：一条 TODO -> 一个最小可验证 OpenSpec task -> 实现 -> 验证 -> 回写状态。
- 禁止一次性跨多个高风险 TODO 混改。

### Step 5: 验证与回写
- 每次修复后必须同步更新：
  - 对应 `docs/design/**` 文档
  - 对应 `docs/todos/*_todo.md` 状态与证据
  - 对应 OpenSpec `tasks.md` 状态
- 验证至少覆盖：测试、接口契约、错误分支、文档一致性。

### Step 6: 归档
- TODO 全部完成后：
  - 将分析文档和 TODO 文档标记为 `archived` 或迁移到历史区块
  - 在 `docs/todos/README.md` 更新索引
  - 在 OpenSpec 完成 archive（如适用）

## 4. 强制门禁（DoD）

- 未完成 Step 1（文档更新）不得进入代码提交。
- 未完成 Step 2（gap 分析）不得创建大于 P2 的实现改动。
- 未完成 Step 3（TODO 映射）不得开始批量修复。
- 未完成 Step 5（验证+回写）不得标记任务完成。
- 未完成 Step 6（归档）不得关闭该轮治理任务。

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
1. 建立/选择 `openspec/changes/<change-id>/`。
2. 创建或更新 `docs/features/<change-id>.md`，并登记 proposal/design/specs/tasks 链接。
3. 按 OpenSpec tasks 逐项执行，每个任务回写证据到 feature 聚合文档与 TODO 文档。
4. 完成后执行 verify + archive，并迁移聚合文档到 `docs/features/archive/`。

### Mode B: 无 OpenSpec 回退（TODO-driven）

仅在 OpenSpec 不可用（工具/环境受限）时使用：
1. 创建 `docs/features/<topic-slug>.md`，并在 frontmatter 声明 `mode: todo_fallback`。
2. 创建日期化 gap/todo 文档对（`docs/todos/`）。
3. 以 TODO 清单推进并持续回写 evidence。
4. OpenSpec 可用后，必须补迁移：将 fallback 资产映射到新的 `openspec/changes/<change-id>/` 并记录迁移证据。

## 8. SOP Skill 化（必须）

SOP 关键阶段必须有可调用技能承载，并保持 checkpoint 与 skill 映射一致：
- kickoff
- execution-sync
- verification
- completion-archive

当前双技能分工：
- 文档管理技能（类型/路径/frontmatter/归档）：
  - `.codex/skills/documentation-management/SKILL.md`
- 开发流程技能（模式选择/checkpoint/证据回写）：
  - `.codex/skills/development-workflow/SKILL.md`

若 SOP 与 skill 行为不一致，以规范文档更新 + skill 同步更新为同一任务，禁止只改其一。
