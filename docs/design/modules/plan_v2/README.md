# Module: plan_v2

> Status: draft baseline for AgentScope D7 gap closure (2026-03-02).

## 1. 定位与职责

- `plan_v2` 提供 Plan Agent 的运行期计划状态容器（`PlannerState`）与计划工具集（`create_plan / validate_plan / revise_current_plan / finish_plan / ...`）。
- 模块目标是让计划具备可追踪生命周期：`todo -> in_progress -> done/abandoned`，并把状态提示通过 `critical_block` 注入执行环。
- 与 `dare_framework/plan` 的关系：`plan` 负责通用 planner/validator 协议；`plan_v2` 负责 AgentScope 兼容路径下的工具化计划状态机。

## 2. 总体架构

- `types.py`：定义 `Task` / `Milestone` / `Step` / `PlannerState` 及状态迁移规则。
- `tools.py`：定义对 `PlannerState` 的唯一写入口（plan tools），并在状态变更后刷新 `critical_block`。
- `planner.py`：作为 `IToolProvider` 暴露 plan tools；由 `ReactAgent` 在执行时挂载消费。
- `prompts.py`：给 Plan Agent 提供固定执行顺序与 tool 使用约束。

## 3. 核心流程

1. Plan Agent 调用 `create_plan` 写入计划与步骤，初始状态为 `todo`。
2. 调用 `validate_plan` 后，计划进入 `in_progress`。
3. 执行阶段通过 sub-agent 工具推进 step 状态迁移。
4. 如需调整计划，调用 `revise_current_plan` 替换或补充步骤。
5. 全部步骤完成后调用 `finish_plan(target_state=\"done\")`，或中止时调用 `finish_plan(target_state=\"abandoned\")`。
6. 每次状态变化都更新 `critical_block`，供 `ReactAgent` 注入下一轮系统提示。

## 4. 数据结构

- `Step`
  - `step_id: str`
  - `description: str`
  - `params: dict[str, Any]`
  - `status: Literal[\"todo\", \"in_progress\", \"done\", \"abandoned\"]`
- `PlannerState`
  - `plan_status: Literal[\"todo\", \"in_progress\", \"done\", \"abandoned\"]`
  - `steps: list[Step]`
  - `completed_step_ids: set[str]`（兼容历史调用路径，和 step 状态保持一致）
  - `critical_block: str`

## 5. 关键接口

- `CreatePlanTool.execute(...)`：创建计划并初始化状态。
- `ValidatePlanTool.execute(...)`：写入验证结果并推动计划进入执行态。
- `ReviseCurrentPlanTool.execute(...)`：在未终态时修订当前计划。
- `FinishPlanTool.execute(...)`：显式完成或放弃计划。
- `SubAgentTool.execute(...)`：按 `step_id` 推进步骤状态并回写进度。

## 6. 异常与错误处理

- 非法状态迁移（如 `done -> in_progress`）必须拒绝并返回结构化错误。
- `finish_plan(target_state=\"done\")` 在存在未完成步骤时必须失败，避免伪完成。
- 对未知 `step_id` 的执行委托必须显式失败，禁止静默跳过。
- 任何状态写入后都必须刷新 `critical_block`，避免提示与真实状态漂移。

## 7. 测试锚点

- `tests/unit/test_plan_v2_tools.py`（状态机迁移、finish/revise、critical_block 联动）
- `tests/unit/test_react_agent_gateway_injection.py`（plan state 注入行为不回归）

