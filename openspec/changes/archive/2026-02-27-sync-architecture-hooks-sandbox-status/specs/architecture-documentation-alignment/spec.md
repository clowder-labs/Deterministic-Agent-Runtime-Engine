## ADDED Requirements

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
