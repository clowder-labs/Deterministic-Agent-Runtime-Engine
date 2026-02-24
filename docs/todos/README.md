# TODO 目录维护说明

> 适用范围：`/docs/todos/`  
> 目标：把项目级待办从“临时记录”变成“可持续维护”的治理清单。

## 1. 目录结构

- `project_overall_todos.md`：项目总体演进 TODO（跨模块、跨阶段）。
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

## 4. 归档规则

- 连续 2 个迭代无动作且不再需要推进的事项，标记为 `dropped` 并说明原因。
- 已完成并稳定 1 个迭代以上的事项，可迁移到“完成记录”分节，避免主清单膨胀。

## 5. 与其他文档的关系

- 与 `docs/design/modules/*`：模块细节在模块文档，这里只保留跨模块视角。
- 与 OpenSpec：执行任务拆解在 OpenSpec artifacts，这里只做方向与优先级治理。
- 与 `docs/README.md`：由文档导航统一入口。
