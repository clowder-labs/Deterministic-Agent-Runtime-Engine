## 1. State Machine Core

- [x] 1.1 在 `plan_v2.types` 定义 step/plan 状态枚举与合法迁移规则。
- [x] 1.2 增加状态同步辅助逻辑，确保 `completed_step_ids` 与 step 状态一致。
- [x] 1.3 补充非法迁移拒绝路径（结构化错误）。

## 2. Plan Tooling

- [x] 2.1 新增 `revise_current_plan` 工具并接入 `Planner`。
- [x] 2.2 新增 `finish_plan` 工具并实现 `done/abandoned` 终态约束。
- [x] 2.3 更新 `create_plan/validate_plan/sub_agent` 的状态推进逻辑。

## 3. Critical Block and Prompt Alignment

- [x] 3.1 更新 `_format_critical_block`：展示 `plan_status` + step 状态 + NEXT 指令。
- [x] 3.2 更新 plan prompt 文案，覆盖 revise/finish 的操作路径。
- [x] 3.3 验证 `critical_block` 在 create/validate/revise/finish 关键节点一致性。

## 4. Verification and Evidence

- [x] 4.1 新增 `tests/unit/test_plan_v2_tools.py` 覆盖状态机与新工具矩阵。
- [x] 4.2 回归测试：定向 plan_v2 + ReactAgent 注入路径。
- [x] 4.3 全量回归：`pytest -q` 并回写 feature evidence。
- [x] 4.4 回写 TODO claim 与 OpenSpec 状态，准备 PR 审查。
