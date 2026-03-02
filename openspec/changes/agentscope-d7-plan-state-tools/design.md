## Context

`plan_v2` 当前提供 `create_plan/validate_plan/...` 等工具，但关键状态依赖 `completed_step_ids` 隐式推导。该方式难以覆盖 AgentScope PlanNoteBook 语义中对 `in_progress`、`abandoned`、显式结束和修订的要求，也让 `critical_block` 的下一步提示缺乏严格状态约束。

## Goals / Non-Goals

**Goals:**
- 引入显式 step/plan 状态机并定义合法迁移。
- 新增 `revise_current_plan` 与 `finish_plan` 工具以补齐 D7 功能缺口。
- 让 `critical_block` 严格反映最新计划状态与下一步建议。
- 保留现有 `completed_step_ids` 兼容字段，避免已有调用链断裂。

**Non-Goals:**
- 本次不实现历史计划恢复（`view_historical_plans/recover_historical_plan`）。
- 本次不引入 plan change hook 回调总线。
- 本次不实现 Session 持久化（`state_dict/load_state_dict` 留在后续切片）。

## Decisions

### Decision 1: 状态机放在 plan_v2 types，工具层只消费
- 在 `types.py` 定义状态常量、合法迁移规则和迁移辅助函数。
- `tools.py` 只通过状态机 API 执行状态变更，非法迁移直接返回错误。
- 理由：避免状态语义散落在多个工具实现里。

### Decision 2: `revise_current_plan` 采用“按 step_id 合并状态”策略
- 修订时允许替换步骤列表，但对同 `step_id` 且已完成步骤保留完成状态。
- 已不存在的新列表步骤会被移除，不再参与 pending。
- 理由：最小化用户修订造成的已完成进度丢失。

### Decision 3: `finish_plan(done)` 必须校验剩余未完成步骤
- 若存在 `todo/in_progress` 步骤，`finish_plan(target_state=\"done\")` 失败。
- `finish_plan(target_state=\"abandoned\")` 会把未终态步骤统一置为 `abandoned`。
- 理由：防止“伪完成”状态污染审计与后续流程。

### Decision 4: `critical_block` 以 plan/step 状态为唯一真相
- 提示块明确展示 `plan_status`、每步状态、pending/completed 列表与下一动作。
- 当全部步骤完成但 plan 未终态时，提示下一步调用 `finish_plan`。
- 理由：降低 agent 提示和实际状态脱节风险。

## Risks / Trade-offs

- [Risk] 增加状态字段后，旧路径若直接写 `completed_step_ids` 可能出现双写不一致。  
  → Mitigation: 提供统一同步函数，把 completed set 从 step 状态派生回写。
- [Risk] `revise_current_plan` 合并规则过宽可能保留错误历史状态。  
  → Mitigation: 仅保留 `done/abandoned` 终态，其它状态回退为 `todo`。
- [Risk] 提示变更会影响 plan agent 行为轨迹。  
  → Mitigation: 更新 prompts 并用单测覆盖 `critical_block` 关键文案分支。

## Migration Plan

1. 在 `types.py` 引入状态机数据结构与合法迁移检查。
2. 增强 `tools.py`（`create/validate/sub_agent` 状态联动）并新增 `revise_current_plan`、`finish_plan`。
3. 更新 `Planner` 与 `__init__` 暴露工具集合，补 prompt 指导语。
4. 编写 D7 单测并执行定向 + 全量回归。
5. 回写 TODO/OpenSpec/feature evidence，并进入 PR 评审。

Rollback:
- 回退新增状态机字段与两项新工具，恢复 `completed_step_ids` 旧逻辑驱动。

## Open Questions

- 后续是否需要新增 `failed` 步骤状态以区分可重试失败与主动放弃？
- `revise_current_plan` 是否需要支持“只补丁变更单个 step”而非全量替换？

