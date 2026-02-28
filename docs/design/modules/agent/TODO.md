# Agent TODO

> 更新日期：2026-02-27
> 说明：Agent 模块唯一补齐清单（用于范围讨论与执行跟踪）

## 1. 本轮范围建议（用于你我讨论）

### 1.1 本轮必须做（推荐）

- [x] A-101 DareAgent 结构化拆分（最小可落地版本）
- [x] A-102 step-driven 路径策略定稿（已实现最小闭环）

### 1.2 可延期（不阻塞当前轮次）

- [x] A-103 统一输出数据形状（output envelope）

## 2. 任务详情与验收

### A-101 DareAgent 结构化拆分（P1）

- 目标：降低单文件复杂度、提高可测试性。
- 建议拆分：
  - `session_orchestrator`
  - `milestone_orchestrator`
  - `execute_engine`
  - `tool_executor`
- 验收标准：
  - [x] `dare_agent.py` 只保留组装与顶层状态转移。
  - [x] 核心循环拥有独立单测，不依赖整 Agent 集成测试。
  - [x] 现有回归测试保持通过。
- 交付证据：
  - `dare_framework/agent/dare_agent.py` 四层 loop 已改为 `_internal` 委托（session/milestone/execute/tool）。
  - `dare_framework/agent/_internal/session_orchestrator.py`
  - `dare_framework/agent/_internal/milestone_orchestrator.py`
  - `dare_framework/agent/_internal/execute_engine.py`
  - `dare_framework/agent/_internal/tool_executor.py`
  - `tests/unit/test_dare_agent_orchestration_split.py`（新增委托边界测试）
  - 受影响回归：`tests/unit/test_five_layer_agent.py`、`tests/unit/test_dare_agent_hook_governance.py`、`tests/unit/test_dare_agent_hook_transport_boundary.py`

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
  - [x] Simple/React/Dare 输出结构一致。
  - [x] `output_text` 与 `output.content` 关系文档化并有回归测试。
- 交付证据：
  - `dare_framework/agent/_internal/output_normalizer.py`（新增 envelope 构造 helper）
  - `dare_framework/agent/simple_chat.py`
  - `dare_framework/agent/react_agent.py`
  - `dare_framework/agent/dare_agent.py`
  - `tests/unit/test_agent_output_envelope.py`
  - 回归：`tests/unit/test_five_layer_agent.py`、`tests/unit/test_builder_tool_gateway.py`
  - 设计同步：`docs/design/modules/agent/README.md`、`docs/design/Interfaces.md`

## 3. 决策记录（每轮更新）

- [x] 本轮选定范围：`A-103`
- [x] 本轮延期项：`无`
- [x] 延期原因：`无`
- [x] 目标落地版本：`codex/a103-output-envelope`
