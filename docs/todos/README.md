# TODO 目录维护说明

> 适用范围：`/docs/todos/`  
> 目标：把项目级待办从“临时记录”变成“可持续维护”的治理清单。

## 1. 目录结构

- `project_overall_todos.md`：项目总体演进 TODO（跨模块、跨阶段）。
- `2026-02-27_full_design_review_gap_analysis.md`：全量设计文档评审差异分析（第二轮刷新，持续治理中）。
- `2026-02-27_full_design_review_gap_todo.md`：全量设计文档评审对应 TODO 清单（持续治理中）。
- `2026-02-27_design_reconstructability_gap_analysis.md`：可重建性差异分析（P0/P1 已闭环，后续与 full-review 联动）。
- `2026-02-27_design_reconstructability_gap_todo.md`：可重建性治理 TODO 清单（已回写 done，待按周期归档）。
- `archive/2026-02-27_design_code_gap_analysis.md`：当前设计与实现差异分析基线（文档先行治理，已归档）。
- `archive/2026-02-27_design_code_gap_todo.md`：由 gap 分析推导出的执行 TODO 清单（已归档）。
- 后续可按需要新增：
  - `YYYY-MM-<topic>.md`：专题治理清单（如测试治理、文档收敛、安全治理）。

## 2. 文档生命周期

每个 TODO 项都建议包含以下字段：

- `ID`：唯一标识（如 `T1-3`）。
- `Priority`：`P0/P1/P2/P3`。
- `Status`：`todo` / `doing` / `blocked` / `done` / `dropped`。
- `Owner`：责任人或责任小组。
- `Evidence`：验证命令、测试结果、PR/commit 或文档链接。
- `Last Updated`：最后更新时间（`YYYY-MM-DD`）。

状态流转建议：

`todo -> doing -> done`  
`todo/doing -> blocked -> doing/dropped`

## 3. 更新规则

- 触发更新：
  - 架构评审后；
  - 里程碑结束后；
  - 出现新的跨模块风险或技术债时。
- 更新要求：
  - 只记录“全局事项”，不写单个 feature 的实现细节；
  - 变更 TODO 时同步更新时间；
  - `done` 项必须补 `Evidence`。
  - 全量设计评审（Architecture + 全部模块 README）至少每两周执行一次，并回写到 `project_overall_todos.md`。

## 4. 归档规则

- 连续 2 个迭代无动作且不再需要推进的事项，标记为 `dropped` 并说明原因。
- 已完成并稳定 1 个迭代以上的事项，可迁移到“完成记录”分节，避免主清单膨胀。
- 归档条目必须使用日期前缀命名，并附对应 OpenSpec change 与验证证据。

## 5. 与其他文档的关系

- 与 `docs/design/modules/*`：模块细节在模块文档，这里只保留跨模块视角。
- 与 OpenSpec：执行任务拆解在 OpenSpec artifacts，这里只做方向与优先级治理（默认模式）。
- 与 `docs/features/*`：每个治理/特性 change 的状态单一真相源在聚合文档，本目录负责分析与执行清单，不重复维护冲突状态。
- 与 `docs/README.md`：由文档导航统一入口。
- 与 `docs/guides/Documentation_First_Development_SOP.md`：必须遵循“gap 分析 -> TODO -> OpenSpec 执行 -> 回写/归档”的闭环流程。
- 与 `docs/governance/Documentation_Management_Model.md`：目录分层、生命周期和回退协作模式以该模型为准。
- 与 `docs/guides/Design_Reconstruction_SOP.md`：重建场景必须遵循该 SOP，并以追踪矩阵为验收入口。
