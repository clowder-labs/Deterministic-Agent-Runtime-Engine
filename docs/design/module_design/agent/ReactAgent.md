# Agent Design: ReactAgent

> Scope: `dare_framework/agent/react_agent.py`

## 1. 设计定位

- 轻量执行模板，使用模型工具调用 + 观察循环完成任务。
- 依赖 ToolGateway / Context；不依赖 Planner/Validator。

## 2. 核心流程

- `run(...)` 进入后写入用户输入 → 直接进入 Execute + Tool Loop。
- 不创建 SessionState / MilestoneState。
- 结束条件：模型不再给出 tool calls 或达到迭代上限。

## 3. 事件与 Hook

- 记录 `react.start` / `react.complete` 事件。
- 触发与 Execute/Tool 相关 HookPhase（BEFORE/AFTER_MODEL、BEFORE/AFTER_TOOL 等）。

## 4. 限制

- 无计划与里程碑验证闭环，结果可信度依赖模型输出。
- 无 milestone 级别的审计与证据管理。
