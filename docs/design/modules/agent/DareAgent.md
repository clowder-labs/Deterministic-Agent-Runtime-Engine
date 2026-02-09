# Agent Design: DareAgent

> Scope: `dare_framework/agent/dare_agent.py`
>
> 本文只描述 DareAgent 的总体设计、模式选择与核心循环；Session 与 Milestone 的详细设计见独立文档：
> - `docs/design/modules/agent/DareAgent_Session.md`
> - `docs/design/modules/agent/DareAgent_Milestone.md`

## 1. 设计定位

- **定位**：完整编排模板，提供 Session → Milestone → Plan → Execute → Tool 的闭环。
- **关键组件**：Planner/Validator/Remediator、ToolGateway、Context、EventLog/Hook/Telemetry。
- **适用场景**：复杂任务、多阶段交付、审计要求高的工作流。

## 2. 运行模式与降级策略

`run_task(...)` 自动选择执行模式：

1. **Full Five-Layer**：存在 planner 或 Task 含 milestones → Session → Milestone → Plan → Execute → Tool
2. **ReAct**：无 planner、有 tools → Execute → Tool
3. **Simple**：无 planner、无 tools → 单次模型调用

> 说明：虽然 DareAgent 能自动降级，但推荐在明确场景下使用 ReactAgent / SimpleChatAgent 以简化行为边界。

## 3. 核心循环概览

- **Plan Loop**：`IPlanner.plan()` → `IValidator.validate_plan()` → `ValidatedPlan`。
- **Execute Loop**：模型调用 → tool calls → Tool Loop → 结果写回 STM → 继续迭代。
- **Plan Tool**：tool name 以 `plan:` 前缀或 registry 标注 `capability_kind=plan_tool` 时，触发 re-plan。
- **Step-driven 预留**：`execution_mode` / `step_executor` / `evidence_collector` 仅保留接口位（TODO）。

> 现状差距：ValidatedPlan.steps 未驱动执行；执行仍由模型在 Execute Loop 自主决定（TODO）。

## 4. 事件与观测

- EventLog（可选）：记录 `session.*`, `plan.*`, `tool.*`, `model.response` 等事件。
- Hooks（可选）：触发 `BEFORE/AFTER_*` 生命周期 HookPhase。
- Telemetry（可选）：通过 ObservabilityHook 输出 traces/metrics/logs。

## 5. Transport 生命周期

- BaseAgent.start() 启动 AgentChannel 并拉起内部 transport loop。
- transport loop 使用 `poll()` 等待输入并调用 `run(...)`；中断通过 `AgentChannel.interrupt()` 取消当前 run。
- BaseAgent.stop() 会取消 transport loop 并停止 AgentChannel。
- `__call__` 等价于 `run(..., transport=None)`。

## 6. 约束与限制

- **安全边界未闭环**：`ISecurityBoundary` 未接入 Agent 主流程。
- **Plan Attempt Isolation 不完整**：STM 没有跨 milestone 的隔离策略，失败计划可能污染上下文。
- **执行控制（HITL）未完备**：仅有 `poll()`/`poll_or_raise()` 调用位，缺少完整审批链。

## 7. Example（Session / Milestone）

```python
from dare_framework.agent import DareAgentBuilder
from dare_framework.plan.types import Task, Milestone

milestones = [
    Milestone(milestone_id="m1", description="collect requirements"),
    Milestone(milestone_id="m2", description="implement core logic"),
    Milestone(milestone_id="m3", description="verify outputs"),
]

task = Task(description="deliver feature X", milestones=milestones)
agent = await (
    DareAgentBuilder("session-demo")
    .with_model(model)
    .with_planner(planner)
    .add_validators(validator)
    .with_remediator(remediator)
    .build()
)

result = await agent.run(task)
print(result.success, result.output)
```
