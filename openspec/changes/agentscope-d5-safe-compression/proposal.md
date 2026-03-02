## Why

AgentScope 迁移里，D5 压缩链路仍未闭环：当前压缩以消息条数为主，缺少 `tool_call/tool_result` 成对保护，也未在模型调用前按 token 预算自动触发。结果是长对话下易出现上下文溢出、工具语义断裂与行为不稳定。

## What Changes

- 增加 D5 切片能力：
  - `tool pair safe` 压缩（禁止孤儿化 tool 调用或结果）；
  - token-aware 压缩阈值与预算收敛；
  - ReAct 模型调用前自动触发压缩。
- 统一压缩策略输入参数与输出标记，便于后续 observability 追踪。
- 增加覆盖 `truncate/summary/tool-pair-safe/auto-trigger` 的回归测试。

## Capabilities

### New Capabilities
- `agentscope-safe-compression`: 在 AgentScope 对齐路径中提供可预测、可验证的安全压缩能力。

### Modified Capabilities
- `chat-runtime`: 模型调用前可按预算自动压缩上下文。
- `context-memory`: 压缩策略对工具消息对保持完整性并支持 token-aware 策略。

## Impact

- Affected code:
  - `dare_framework/compression/core.py`
  - `dare_framework/context/context.py`
  - `dare_framework/agent/react_agent.py`
- Affected tests:
  - `tests/unit/test_context_implementation.py`
  - `tests/unit/test_agent_output_envelope.py`
  - `tests/unit/test_example_10_agentscope_compat.py`
- No external dependency change.
