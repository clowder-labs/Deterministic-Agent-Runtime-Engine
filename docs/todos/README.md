# TODO 目录维护说明

> 适用范围：`/docs/todos/`  
> 目标：把项目级待办从“临时记录”变成“可持续维护”的治理清单。

## 1. 目录结构

- `project_overall_todos.md`：项目总体演进 TODO（跨模块、跨阶段）。
- `YYYY-MM-DD_<change-id>_execution_todos.md`：活跃 change 的执行协作板，用于多人协作、Gate 冻结与回写。
- `2026-02-27_full_design_review_gap_analysis.md`：全量设计文档评审差异分析（第二轮刷新，持续治理中）。
- `2026-02-27_full_design_review_gap_todo.md`：全量设计文档评审对应 TODO 清单（持续治理中）。
- `2026-02-27_design_reconstructability_gap_analysis.md`：可重建性差异分析（P0/P1 已闭环，后续与 full-review 联动）。
- `2026-02-27_design_reconstructability_gap_todo.md`：可重建性治理 TODO 清单（已回写 done，待按周期归档）。
- `2026-03-02_client_cli_host_orchestration_gap_analysis.md`：Issue #135 的 `/client` 宿主编排协议差距分析（活跃）。
- `2026-03-02_client_cli_host_orchestration_master_todo.md`：Issue #135 对应 master TODO 与切片规划（活跃）。
- `archive/2026-02-27_design_code_gap_analysis.md`：当前设计与实现差异分析基线（文档先行治理，已归档）。
- `archive/2026-02-27_design_code_gap_todo.md`：由 gap 分析推导出的执行 TODO 清单（已归档）。
- `templates/change_execution_todo_template.md`：活跃 change 执行协作板模板。
- 后续可按需要新增：
  - `YYYY-MM-<topic>.md`：专题治理清单（如测试治理、文档收敛、安全治理）。

## 2. 三层职责划分

- `docs/design/TODO_INDEX.md`：设计 backlog / 发现池。只回答“还有什么设计 TODO”，不用于认领。
- `docs/todos/project_overall_todos.md`：项目路线图 + 外层 `Claim Ledger`。记录跨模块、跨阶段事项，并声明“哪一段 scope 当前由谁推进”。
- `docs/todos/YYYY-MM-DD_<change-id>_execution_todos.md`：活跃 change 的内层协作执行板。回答“这一 change 内部如何拆 work package、依赖谁、冻结到哪一层、证据在哪里”。

规则：

- 不要把单个 feature 的实现细节或 work package 填进 `project_overall_todos.md`。
- `project_overall_todos.md` 可以声明路线图级 `Claim Ledger`，但不替代 active change 内部的 execution board。
- 不要直接从 `TODO_INDEX` 抢任务；必须先落到 TODO scope，再视协作复杂度决定是否创建 execution board。
- 当 active change 存在多人并行、共享接口风险、或需要 Gate 冻结时，必须有一份 execution board，并与对应 `openspec/changes/<change-id>/tasks.md` 双向关联。

## 3. 文档生命周期

每个 TODO 项都建议包含以下字段：

- `ID`：唯一标识（如 `T1-3`）。
- `Priority`：`P0/P1/P2/P3`。
- `Status`：`todo` / `doing` / `blocked` / `done` / `dropped`。
- `Owner`：责任人或责任小组。
- `Claim Status`：`planned` / `active` / `released` / `done` / `expired`。
- `Claim Expires`：认领过期时间（`YYYY-MM-DD`）。
- `Evidence`：验证命令、测试结果、PR/commit 或文档链接。
- `Last Updated`：最后更新时间（`YYYY-MM-DD`）。

状态流转建议：

`todo -> doing -> done`  
`todo/doing -> blocked -> doing/dropped`

### 3.1 外层认领声明（Claim Ledger）

每个活跃 TODO 文档都应包含 `Claim Ledger` 区块，用于声明“哪一段 TODO scope 当前由谁推进”。

建议字段：

- `Claim ID`：唯一认领编号（如 `CLM-20260302-A1`）。
- `TODO Scope`：被认领的 TODO ID 范围（如 `T5-2`、`D2-1~D2-4`）。
- `Owner`：当前负责人。
- `Status`：`planned` / `active` / `released` / `done` / `expired`。
- `Declared At`：声明时间（`YYYY-MM-DD`）。
- `Expires At`：过期时间（建议 1-7 天，超时需续期或释放）。
- `OpenSpec Change`：对应 change-id；尚未建立时写 `pending`。
- `Notes`：冲突说明、续期原因、交接备注。

执行规则：

- 在 TODO 进入实现前，必须先写入 `Claim Ledger`。
- 同一 TODO scope 在同一时刻只能有一个 `planned/active` 认领。
- 到期未续期的认领应转为 `expired`，并允许他人重新认领。
- `Claim Ledger` 只声明 ownership，不替代 active change 的协作拆包。

## 4. Spec-Driven 协作粒度

默认原则：`外层认领 scope，内层拆 work package，小 task 验收`。

### 4.1 认领单位

- 外层 `Claim Ledger` 的认领单位应为 `TODO slice` 或 `change scope`，不是单个 bullet，也不是整个模块。
- 内层 execution board 的协作单位才是 `work package`。
- 一个 `TODO slice` 通常映射一个 active change；一个 active change 内部再拆成 `2-5` 个 `work package`。

### 4.2 work package 必须满足

- 单一 owner。
- 单一主要目标。
- 单一冻结边界：最多跨 1 个 Gate。
- 可独立验证：有明确测试、联调或文档证据。
- Touch scope 可提前声明，避免多人同时修改同一组核心文件。

### 4.3 子任务的用途

- 子任务保留细粒度，用于验收、review、回写、证据映射。
- 子任务通常对应 OpenSpec `tasks.md` 的 checkbox、gap ID、测试项或接口契约项。
- 除非一个 work package 被正式拆包，否则子任务本身不单独认领。

### 4.4 推荐状态流转

- `todo -> claimed -> doing -> review -> done`
- `todo/claimed/doing -> blocked -> doing/dropped`

`claimed` 表示“已经占坑但尚未进入实做”；超过 24 小时未推进，建议释放。
`review` 表示实现已完成，等待 PR review / 联调验证 / 文档回写。

### 4.5 执行门禁

- 先做 claim：`Claim Ledger` 先写入 scope/owner/expires/change-id。
- 再做 spec-sync：设计文档、gap analysis、execution board、OpenSpec artifacts 先入库。
- 然后提交 docs-only `intent PR`：只包含 claim/spec/docs/board，不允许夹带实现代码。
- 只有 `intent PR` 合入 `main` 后，才允许对应 work package 进入 `claimed/doing` 和正式实现。
- 共享接口先冻结再并行：schema、payload、状态机、审计字段等共享契约必须先经过 Gate 冻结，再放行下游并行实现。

## 5. execution board 建议字段

对 `work package`，建议至少记录：

- `WP`：唯一标识，如 `WP-A`。
- `Goal`：该包的独立目标。
- `Owner`：唯一负责人。
- `Depends On`：依赖的上游包或 Gate。
- `Touch Scope`：预计修改的目录/文件集合。
- `Freeze Gate`：本包依赖或产出的冻结点。
- `Status`：`todo/claimed/doing/review/blocked/done/dropped`。
- `Branch/Worktree`：分支或工作树路径。
- `PR`：关联 PR。
- `Evidence`：测试、联调、设计回写证据。
- `Last Updated`：最后更新时间。

模板与示例：

- 模板：`docs/todos/templates/change_execution_todo_template.md`
- 参考实例：`docs/todos/agentscope_domain_execution_todos.md`

## 6. 更新规则

- 触发更新：
  - 架构评审后；
  - 里程碑结束后；
  - 出现新的跨模块风险或技术债时。
- 更新要求：
  - 只记录“全局事项”，不写单个 feature 的实现细节；
  - 变更 TODO 时同步更新时间；
  - `done` 项必须补 `Evidence`。
  - 进入实现前必须先更新 `Claim Ledger`。
  - 进入实现前必须先完成 docs-only `intent PR` 合入。
  - 全量设计评审（Architecture + 全部模块 README）至少每两周执行一次，并回写到 `project_overall_todos.md`。

对 active execution board，额外要求：

- 认领发生变化时，同步更新 `Owner/Status/Branch/Last Updated`。
- `intent PR` 中必须至少包含 board 骨架、Gate 定义和 Touch Scope。
- Gate 冻结时，必须补“冻结内容 + 证据链接”。
- `done` 前必须确认 OpenSpec `tasks.md` 与 execution board 状态一致。

## 7. 归档规则

- 连续 2 个迭代无动作且不再需要推进的事项，标记为 `dropped` 并说明原因。
- 已完成并稳定 1 个迭代以上的事项，可迁移到“完成记录”分节，避免主清单膨胀。
- 归档条目必须使用日期前缀命名，并附对应 OpenSpec change 与验证证据。

active execution board 归档前应满足：

- 对应 OpenSpec change 已完成或明确停止。
- 关键 Gate 已标记最终状态。
- 所有 `done/dropped` 包均有证据或原因。

## 8. 与其他文档的关系

- 与 `docs/design/modules/*`：模块细节在模块文档，这里只保留跨模块视角。
- 与 OpenSpec：执行任务拆解在 OpenSpec artifacts，这里只做方向与优先级治理（默认模式）。
- 与 `docs/features/*`：每个治理/特性 change 的状态单一真相源在聚合文档，本目录负责分析与执行清单，不重复维护冲突状态。
- 与 `docs/README.md`：由文档导航统一入口。
- 与 `docs/guides/Documentation_First_Development_SOP.md`：必须遵循“gap 分析 -> TODO -> OpenSpec 执行 -> 回写/归档”的闭环流程。
- 与 `docs/governance/Documentation_Management_Model.md`：目录分层、生命周期和回退协作模式以该模型为准。
- 与 `docs/guides/Design_Reconstruction_SOP.md`：重建场景必须遵循该 SOP，并以追踪矩阵为验收入口。
