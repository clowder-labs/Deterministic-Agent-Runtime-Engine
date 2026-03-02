## Why

AgentScope 迁移的首要阻断在于两条链路未闭环：一是模型 `thinking` 内容在响应结构中丢失，二是 transport 无法稳定表达 `thinking/tool_call/tool_result` 中间态事件。若不先补齐该切片，后续压缩、计划、审计等能力会持续依赖 shim，无法进入框架原生实现。

## What Changes

- 新增一组面向 AgentScope 对齐的运行态能力：
  - 模型响应保留 `thinking_content`；
  - usage 规范化 `reasoning_tokens`；
  - ReAct 执行链路输出 `thinking/tool_call/tool_result` 中间态事件。
- 统一 transport 事件语义，明确 `message/tool_call/tool_result/thinking/error/status` 的规范映射。
- 统一 payload/error 契约并补齐回归测试，保证 CLI 与 transport 一致消费。

## Capabilities

### New Capabilities
- `agentscope-thinking-transport`: 定义并落地 AgentScope 对齐所需的 thinking + tool 中间态事件契约与模型响应保真能力。

### Modified Capabilities
- `transport-channel`: 增加中间态事件分类与错误载荷一致性要求。
- `chat-runtime`: 增加模型 `thinking_content` 与 `reasoning_tokens` 规范化要求。

## Impact

- Affected code:
  - `dare_framework/transport/*`
  - `dare_framework/model/types.py`
  - `dare_framework/model/adapters/openai_adapter.py`
  - `dare_framework/model/adapters/openrouter_adapter.py`
  - `dare_framework/agent/react_agent.py`
- Affected tests:
  - `tests/unit/test_transport_types.py`
  - `tests/unit/test_transport_channel.py`
  - `tests/unit/test_openrouter_adapter.py`
  - `tests/unit/test_agent_event_transport_hook.py`
- No external dependency change; compatibility path keeps legacy alias mapping where required.
