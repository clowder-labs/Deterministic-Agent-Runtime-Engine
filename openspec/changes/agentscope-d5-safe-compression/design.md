## Context

当前 `compress_context` 主要支持按条数截断、去重截断与启发式摘要；`ReactAgent` 仅做预算累计与检查，并未在调用模型前自动压缩。对于包含工具调用的长链路，这会导致历史中 `assistant(tool_calls)` 与 `tool` 结果被拆断，降低后续轮次可解释性与稳定性。

## Goals / Non-Goals

**Goals:**
- 保证压缩后不会产生孤儿 `tool_call` 或 `tool_result`。
- 在 token 预算紧张时自动触发压缩并继续执行。
- 给压缩结果打上稳定策略标记，支持后续日志/审计。

**Non-Goals:**
- 不在本切片引入新的 LLM provider。
- 不在本切片实现跨 session 持久化压缩策略。
- 不在本切片实现完整可配置策略中心（仅补最小必要参数）。

## Decisions

1. **tool pair safe 作为压缩后置保护**
- Decision: 在压缩得到候选消息序列后，执行一次成对校验与修复，确保 `assistant.tool_calls` 与对应 `tool` 消息同留或同删。
- Rationale: 兼容现有压缩策略，实现侵入最小。

2. **token-aware 触发采用轻量估算优先**
- Decision: 复用现有 token 估算启发式，在 `max_tokens` 预算接近阈值时触发压缩；后续可扩展为 provider 真实 tokenizer。
- Rationale: 本轮优先闭环能力与稳定性，避免引入额外依赖。

3. **自动触发放在 ReAct 模型调用前**
- Decision: 在 `ReactAgent.execute` 每轮组装消息后、`model.generate` 前判断并触发 `context.compress(...)`。
- Rationale: 时序明确，且能覆盖多轮工具调用场景。

4. **验证采用“策略单测 + 执行链路回归”**
- Decision: 压缩核心做策略级单测；ReAct 做触发时序与非回归测试。
- Rationale: 同时保障算法正确性与运行时行为。

## Risks / Trade-offs

- [Risk] 压缩策略更积极可能影响模型回答质量。  
  Mitigation: 先默认保守阈值，保留回滚开关。
- [Risk] tool-pair 保护增加实现复杂度。  
  Mitigation: 仅覆盖单轮内标准 `tool_call_id` 匹配语义并补回归。

## Migration Plan

1. 扩展压缩 core：pair-safe + token-aware 策略。
2. 接入 ReAct 自动触发点并补保护参数。
3. 补齐 D5 回归测试矩阵并跑全量测试。
4. 回写 feature evidence 与 TODO 状态。

Rollback:
- 如出现行为回归，可关闭自动触发，仅保留手动压缩路径。
