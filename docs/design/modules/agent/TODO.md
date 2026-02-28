# Agent TODO

> 更新日期：2026-02-27
> 说明：Agent 模块唯一补齐清单（用于范围讨论与执行跟踪）

## 1. 本轮范围建议（用于你我讨论）

### 1.1 本轮必须做（推荐）

- [ ] A-101 DareAgent 结构化拆分（最小可落地版本）
- [x] A-102 step-driven 路径策略定稿（已实现最小闭环）

### 1.2 可延期（不阻塞当前轮次）

- [ ] A-103 统一输出数据形状（output envelope）

## 2. 任务详情与验收

### A-101 DareAgent 结构化拆分（P1）

- 目标：降低单文件复杂度、提高可测试性。
- 建议拆分：
  - `session_orchestrator`
  - `milestone_orchestrator`
  - `execute_engine`
  - `tool_executor`
- 验收标准：
  - [ ] `dare_agent.py` 只保留组装与顶层状态转移。
  - [ ] 核心循环拥有独立单测，不依赖整 Agent 集成测试。
  - [ ] 现有回归测试保持通过。

### A-102 step-driven 路径闭环（P1）

- 现状：`execution_mode="step_driven"` 已接入主执行链，`ValidatedPlan.steps` 通过 `IStepExecutor` 顺序执行。
- 实施策略（二选一，必须先定）：
  - [x] A 方案：实现最小 step-driven 闭环。
  - [ ] B 方案：当前阶段明确不支持，并删除无效配置位。
- 验收标准：
  - [x] 设计文档与实现一致（无“文档承诺但实现缺失”）。
  - [x] 至少覆盖 `happy path + failure path`。

### A-103 统一输出数据形状（P2）

- 目标：跨 agent 统一 `RunResult.output` 结构，降低上层解析复杂度。
- 建议结构：
  - `{"content": str, "metadata": dict, "usage": dict | None}`
- 验收标准：
  - [ ] Simple/React/Dare 输出结构一致。
  - [ ] `output_text` 与 `output.content` 关系文档化并有回归测试。

## 3. 决策记录（每轮更新）

- [ ] 本轮选定范围：`______`
- [ ] 本轮延期项：`______`
- [ ] 延期原因：`______`
- [ ] 目标落地版本：`______`
