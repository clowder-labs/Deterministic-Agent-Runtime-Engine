## Why

AgentScope 兼容差距中，PlanNoteBook 相关能力仍缺关键闭环：步骤与计划状态机不完整、计划不可修订、计划无法显式完成/放弃。当前 `plan_v2` 仅依赖 `completed_step_ids` 追踪进度，难以表达 `in_progress/abandoned` 等中间态，导致执行提示与真实状态可能漂移。

## What Changes

- 为 `plan_v2` 补齐 `todo/in_progress/done/abandoned` 状态机（step + plan）。
- 新增 `revise_current_plan` 工具，支持计划创建后的结构化修订。
- 新增 `finish_plan` 工具，支持显式完成/放弃并执行状态约束校验。
- 将 `critical_block` 与状态机联动，确保下一步提示由真实状态驱动。
- 增加 D7 单测矩阵（合法/非法迁移、finish/revise、critical block、回归兼容）。

## Capabilities

### New Capabilities
- `agentscope-plan-state-machine`: 面向 plan_v2 的标准状态迁移与终态收敛。
- `agentscope-plan-revision-tools`: 计划运行时修订与显式结束工具能力。

### Modified Capabilities
- `chat-runtime`: plan `critical_block` 的状态提示由新状态机驱动，减少执行引导偏差。

## Impact

- Affected code:
  - `dare_framework/plan_v2/types.py`
  - `dare_framework/plan_v2/tools.py`
  - `dare_framework/plan_v2/planner.py`
  - `dare_framework/plan_v2/__init__.py`
  - `dare_framework/plan_v2/prompts.py`
  - `tests/unit/test_plan_v2_tools.py` (new)
- Runtime/API impact:
  - 新增计划工具（`revise_current_plan`、`finish_plan`）并扩展状态字段。
  - 计划执行提示从“已完成集合”升级为“显式状态机”。

