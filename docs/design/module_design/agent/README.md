# Module: agent

> Status: aligned to `dare_framework/agent` (2026-02-04). Agent 设计按类型拆分，DareAgent 的 Session / Milestone 有独立详细设计。

## 1. 定位与职责

- 提供对外最小运行面：`IAgent.run(...)`。
- 承载编排策略（多实现），当前主实现为 `DareAgent`（五层循环 + 降级模式）。
- 负责串联 Context / Model / Tool / Plan / Event / Hook 等模块的运行时协作。

## 2. 通用概念与接口

- **任务与结果**：`Task` / `Milestone` / `RunResult`（`dare_framework/plan/types.py`）。
- **通用接口**：`IAgent` / `IAgentOrchestration`（`dare_framework/agent/kernel.py`, `interfaces.py`）。
- **基础类**：`BaseAgent`（统一 transport 生命周期与运行入口）。
- **模型与工具边界**：`ModelInput` / `ModelResponse`、`ToolLoopRequest` / `Envelope`。

## 3. Agent 类型设计文档（按形态区分）

- **DareAgent**（五层循环模板）
  - 设计总览：`docs/design/module_design/agent/DareAgent.md`
  - Session 设计：`docs/design/module_design/agent/DareAgent_Session.md`
  - Milestone 设计：`docs/design/module_design/agent/DareAgent_Milestone.md`

- **ReactAgent**（ReAct 工具循环模板）
  - 设计总览：`docs/design/module_design/agent/ReactAgent.md`

- **SimpleChatAgent**（单轮对话模板）
  - 设计总览：`docs/design/module_design/agent/SimpleChatAgent.md`

## 4. 扩展点（共通）

- 自定义编排：实现 `IAgentOrchestration`，或继承 `BaseAgent`。
- 替换组件：通过 Builder 注入自定义 model / planner / validator / tool gateway / context。
- 运行时上下文：通过 `with_run_context_factory(...)` 注入 Tool RunContext。

## 5. 约束与限制（共通）

- **安全边界未闭环**：`ISecurityBoundary` 未接入 Agent 主流程。
- **执行控制（HITL）未完备**：仅有 `poll()`/`poll_or_raise()` 调用位，缺少完整审批链。
- **Hooks 已接入**：DareAgent 会触发 HookPhase 生命周期事件；React/Simple 仅触发核心执行阶段。

## 6. Assessment

- 评估报告：`docs/design/module_design/agent/Assessment.md`
