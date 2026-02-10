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
  - 设计总览：`docs/design/modules/agent/DareAgent.md`
  - Session 设计：`docs/design/modules/agent/DareAgent_Session.md`
  - Milestone 设计：`docs/design/modules/agent/DareAgent_Milestone.md`

- **ReactAgent**（ReAct 工具循环模板）
  - 设计总览：`docs/design/modules/agent/ReactAgent.md`

- **SimpleChatAgent**（单轮对话模板）
  - 设计总览：`docs/design/modules/agent/SimpleChatAgent.md`

## 4. 扩展点（共通）

- 自定义编排：实现 `IAgentOrchestration`，或继承 `BaseAgent`。
- 替换组件：通过 Builder 注入自定义 model / planner / validator / tool gateway / context。
- 运行时工具上下文：通过 `with_config(Config(...))` 注入（例如 `workspace_dir`、`tools` 配置）。

## 5. 约束与限制（共通）

- **安全边界未闭环**：`ISecurityBoundary` 未接入 Agent 主流程。
- **执行控制（HITL）未完备**：仅有 `poll()`/`poll_or_raise()` 调用位，缺少完整审批链。
- **Hooks 已接入**：DareAgent 会触发 HookPhase 生命周期事件；React/Simple 仅触发核心执行阶段。

## 6. Assessment

- 评估报告：`docs/design/modules/agent/Assessment.md`

## 7. 开发约束（Agent）

- 强类型优先：Agent 运行路径中的状态、控制、动作等语义必须通过枚举/类型对象表达，禁止在 domain 层通过字符串解析推断行为。
- 边界解码：仅协议/适配器边界允许处理原始字符串或松散字典；进入 Agent 核心流程前必须完成类型化。
- 接口约束：默认使用 `ABC` 定义框架接口；仅在确需结构化子类型匹配时使用 `Protocol`（当前优先用于 Model 相关抽象）。
- 开发期策略：当前框架处于开发阶段，不引入历史兼容分支或保护性回退逻辑，发现不合理设计直接重构。
- Python 基线：最低兼容版本为 Python `3.12`，不再为 `3.11` 及更老版本添加兼容代码。
