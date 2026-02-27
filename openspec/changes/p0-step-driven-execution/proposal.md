## Why

当前五层循环中 `ValidatedPlan.steps` 已有数据结构，但执行环路仍主要由模型即时 `tool_calls` 驱动，导致“计划可验证”与“执行可追踪”之间存在断层。P0 需要把 step 计划变成可落地执行路径，减少模型自由漂移并提升可审计性。

## What Changes

- 启用 `execution_mode` 的真实分支行为，支持 `model_driven` 与 `step_driven` 两种执行路径。
- 在 `step_driven` 模式下按 `ValidatedPlan.steps` 顺序执行，并输出结构化 `StepResult` 与 `Evidence`。
- 将现有 `IStepExecutor` / `DefaultStepExecutor` 接入主循环，统一失败中断与错误聚合策略。
- 补齐无 validator 场景下的最小 step 转换逻辑，避免当前 `steps=[]` 的信息丢失。
- 将 step 执行产物纳入 milestone verify 输入，形成“plan -> execute -> verify”闭环。

## Capabilities

### New Capabilities
- `step-driven-execution`: 基于 `ValidatedPlan.steps` 的确定性执行模式，支持顺序执行、证据采集与失败处理。

### Modified Capabilities
- `plan-module`: 将 plan step 从“描述性数据”升级为“可执行输入”。
- `session-loop`: 调整 execute loop 行为，使其支持按配置切换执行模式。
- `core-runtime`: 增强运行时输出结构，支持 step 级结果与 evidence 聚合。

## Impact

- Affected code:
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/_internal/step_executor.py`
  - `dare_framework/agent/builder.py`
  - `dare_framework/plan/interfaces.py`
  - `dare_framework/plan/types.py`
  - `tests/unit/test_five_layer_agent.py`
  - `tests/integration/test_example_agent_flow.py`
- Runtime/API impact:
  - `execution_mode` 从注释字段变为生效行为，错误策略将更确定。
  - step 执行结果将进入验证阶段，提高外部可验证性。
