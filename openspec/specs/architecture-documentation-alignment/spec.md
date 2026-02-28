# architecture-documentation-alignment Specification

## Purpose
Define baseline requirements that keep `docs/design/Architecture.md` aligned with implemented runtime facts for Hook integration and Plan Attempt sandbox isolation.

## Requirements
### Requirement: Architecture 文档必须反映 Hook 接入基线

`docs/design/Architecture.md` SHALL 将 Hook 相关状态描述为“已接入生命周期触发点的基线能力”，并在同一段落明确 payload schema/扩展策略仍可继续完善，避免使用“未接入”等与实现冲突的断言。

#### Scenario: 架构图与状态说明一致反映 Hook 基线
- **WHEN** 评审者阅读 Architecture 架构图与 Hook 特性段落
- **THEN** 可以看到 Hook 接入状态为已落地基线，而非“未接入”
- **AND** 文档仍明确 payload 规范化是后续工作

### Requirement: Architecture 文档必须反映 Plan Attempt Sandbox 基线

`docs/design/Architecture.md` SHALL 描述 Plan Attempt Isolation 当前基线为 STM snapshot/rollback/commit 机制已接入，并区分“基线已实现”与“更严格隔离语义仍待扩展”。

#### Scenario: Isolation 约束段落不再宣称 snapshot/rollback 缺失
- **WHEN** 评审者查看 Plan Attempt Isolation 小节
- **THEN** 文档不再包含“引入 snapshot/rollback”的待实现断言
- **AND** 文档明确当前隔离范围及剩余改进方向

### Requirement: DG-001 完成后必须回写证据

当 DG-001 任务完成时，`docs/todos/archive/2026-02-27_design_code_gap_todo.md` MUST 将该项状态更新为 `done` 并附上可定位的文件证据。

#### Scenario: TODO 状态与证据已更新
- **WHEN** 维护者检查 DG-001 对应 TODO 行
- **THEN** 状态为 `done`
- **AND** Evidence 字段包含本次 OpenSpec change 路径与文档文件路径

### Requirement: Architecture 与模块设计文档必须执行完整评审

`docs/design` 的治理流程 MUST 支持“完整评审”模式：一次评审中至少覆盖 `Architecture.md` 与全部 `docs/design/modules/*/README.md`，并识别与当前实现冲突的断言。

#### Scenario: 完整评审覆盖范围可核验

- **WHEN** 维护者执行一次设计文档评审
- **THEN** 评审结果包含 Architecture 与全部模块 README 的检查结论
- **AND** 结论至少区分 `aligned` / `drift` 两类状态

### Requirement: Architecture 文档不得保留已失效的核心运行态断言

`docs/design/Architecture.md` MUST 与当前核心运行态一致，不得继续宣称以下已落地能力“未实现”：step-driven execute loop、plan/tool security gate、plan attempt sandbox baseline。

#### Scenario: 核心运行态断言与代码一致

- **WHEN** 评审者阅读 Architecture 的“现实差距 / 核心流程”章节
- **THEN** 不存在“ValidatedPlan.steps 未驱动执行”或“security gate 未接入”等失效断言
- **AND** 文档仅保留仍未闭环的能力作为 TODO

### Requirement: 完整评审结果必须沉淀为 gap 分析与 TODO 清单

每次完整评审 MUST 在 `docs/todos/` 生成对应的 gap 分析文档与 TODO 清单，并给出可追溯证据链接。

#### Scenario: 评审产物具备可追溯性

- **WHEN** 维护者检查该轮评审产物
- **THEN** 可定位到 gap 文档、TODO 文档和对应实现/文档证据

### Requirement: Architecture 文档必须维护审批语义决策表

`docs/design/Architecture.md` MUST 包含 plan/tool 两入口的审批语义决策表，明确当前行为、目标行为与迁移策略。

#### Scenario: 审批语义差异可被识别

- **WHEN** 评审者阅读 Architecture 的安全与审批章节
- **THEN** 可看到 plan/tool 入口语义差异与统一策略
- **AND** 不需要从代码逆向推断行为

### Requirement: Architecture 文档必须链接可重建性追踪矩阵

`docs/design/Architecture.md` MUST 提供可重建性追踪矩阵入口，使关键架构约束可跳转到实现与测试证据。

#### Scenario: 架构约束能追踪到实现与测试

- **WHEN** 评审者查看某条架构不变量
- **THEN** 可通过文档链接定位到对应代码与测试证据
