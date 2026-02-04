# Module: agent

> Status: aligned to `dare_framework/agent` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 提供对外最小运行面：`IAgent.run(...)`。
- 承载编排策略（多实现），当前主实现为 `DareAgent`（五层循环 + 降级模式）。
- 负责串联 Context / Model / Tool / Plan / Event / Hook 等模块的运行时协作。

## 2. 关键概念与数据结构

- `Task` / `Milestone` / `RunResult`：任务输入与输出（`dare_framework/plan/types.py`）。
- `SessionState` / `MilestoneState`：运行时状态与证据/反思记录（`dare_framework/agent/_internal/orchestration.py`）。
- `ModelInput` / `ModelResponse`：模型调用输入输出（`dare_framework/model/types.py`）。
- `ToolLoopRequest` / `Envelope`：工具调用边界与预算（`dare_framework/plan/types.py`）。

## 3. 核心流程（当前实现）

### 3.1 运行模式

`DareAgent.run(...)` 根据组件配置自动选择：

1. **Simple Mode**：无 planner、无 tool_gateway → 单次模型调用。
2. **ReAct Mode**：无 planner、有 tool_gateway → Execute + Tool Loop。
3. **Five-Layer Mode**：有 planner 或 Task 含 milestones → Session → Milestone → Plan → Execute → Tool。

### 3.2 五层编排要点

- **Plan Loop**：`IPlanner.plan()` 生成 `ProposedPlan`，`IValidator.validate_plan()` 生成 `ValidatedPlan`。
- **Execute Loop**：模型调用 → tool calls → Tool Loop → 结果写回 STM → 继续迭代。
- **Plan Tool**：tool name 以 `plan:` 前缀或 registry 标注 `capability_kind=plan_tool` 时，触发 re-plan。

> 现状差距：ValidatedPlan.steps 未驱动执行；执行仍由模型在 Execute Loop 自主决定（TODO）。

### 3.3 事件与观测

- 若提供 `IEventLog`，Agent 会记录 `session.*`, `plan.*`, `tool.*`, `model.response` 等事件。
- DareAgent 会在关键阶段触发 Hook（BEFORE/AFTER_*），并可通过 transport 输出 hook envelope。

### 3.4 Transport 生命周期（start/stop）

- BaseAgent.start() 会启动 AgentChannel 并拉起内部 transport loop。
- transport loop 使用 `poll()` 等待输入并调用 `run(...)`；中断通过 `AgentChannel.interrupt()` 取消当前 run。
- BaseAgent.stop() 会取消 transport loop 并停止 AgentChannel。
- `__call__` 是 `run(..., transport=None)` 的便捷调用形式。

## 4. 关键接口与实现

- Kernel：`IAgent`（`dare_framework/agent/kernel.py`）
- 编排策略接口：`IAgentOrchestration`（`dare_framework/agent/interfaces.py`）
- 默认实现：`DareAgent`（`dare_framework/agent/five_layer.py`）
- 轻量实现：`SimpleChatAgent`（`dare_framework/agent/simple_chat.py`）、`ReactAgent`（`dare_framework/agent/react_agent.py`）
- Builder：`DareAgentBuilder` / `ReactAgentBuilder` / `SimpleChatAgentBuilder`（`dare_framework/agent/builder.py`）

## 5. 与其他模块的交互

- **Context**：写入 STM（user/assistant/tool messages），调用 `assemble()` 生成模型输入。
- **Model**：调用 `IModelAdapter.generate(...)` 获取响应与 tool calls。
- **Tool**：调用 `IToolGateway.invoke(...)` 执行工具；Tool Loop 应用 `Envelope` 约束。
- **Plan**：planner/validator/remediator 可选注入；验证结果影响 re-plan。
- **Event**：可选 EventLog 记录审计事件。
- **Hook**：可选 Hook（DareAgent 已接入并触发生命周期事件）。

## 6. 约束与限制（当前实现）

- **安全边界未闭环**：`ISecurityBoundary` 未接入 Agent 主流程。
- **Plan Attempt Isolation 不完整**：STM 没有隔离计划尝试，失败计划可能污染上下文。
- **执行控制（HITL）未完备**：仅有 `poll()`/`poll_or_raise()` 调用位，缺少完整审批链。
- **Hooks 已接入**：DareAgent 会触发 HookPhase 生命周期事件。

## 7. 扩展点

- 自定义编排：实现 `IAgentOrchestration`，或继承 `BaseAgent`。
- 替换组件：通过 Builder 注入自定义 model / planner / validator / tool gateway / context。
- 运行时上下文：通过 `with_run_context_factory(...)` 注入 Tool RunContext。

## 8. TODO / 未决问题

- TODO: 将 ValidatedPlan.steps 驱动 Execute Loop（计划执行一致性）。
- TODO: 引入 plan attempt snapshot/rollback，实现失败计划隔离。
- TODO: 接入 `ISecurityBoundary`（policy gate + trust derivation）。
- TODO: Hook payload schema 与默认 hook 管理器。
- TODO: 对齐 EventLog / HITL 事件链（pause → wait → resume）。

## 9. Design Clarifications (2026-02-03)

- Impl gap: Builder `build()` returns `Any`; should return concrete agent type.
- Impl gap: transport loop is internal (`_run_transport_loop`); keep start/stop as public lifecycle.
- Doc gap: reflect hook emissions and transport lifecycle semantics.
