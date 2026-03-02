---
change_ids: ["agentscope-d2-d4-thinking-transport"]
doc_kind: feature
topics: ["agentscope", "transport", "thinking", "tool-events", "model-response"]
created: 2026-03-02
updated: 2026-03-02
status: draft
mode: openspec
---

# Feature: agentscope-d2-d4-thinking-transport

## Scope
补齐 AgentScope 迁移中最先阻断执行闭环的 D2 + D4 能力：统一 transport 中间态事件协议，并在模型与执行循环中保留/输出 thinking 与 reasoning usage 信息。

## OpenSpec Artifacts
- Proposal: `openspec/changes/agentscope-d2-d4-thinking-transport/proposal.md`
- Design: `openspec/changes/agentscope-d2-d4-thinking-transport/design.md`
- Specs:
  - `openspec/changes/agentscope-d2-d4-thinking-transport/specs/agentscope-thinking-transport/spec.md`
  - `openspec/changes/agentscope-d2-d4-thinking-transport/specs/transport-channel/spec.md`
  - `openspec/changes/agentscope-d2-d4-thinking-transport/specs/chat-runtime/spec.md`
- Tasks: `openspec/changes/agentscope-d2-d4-thinking-transport/tasks.md`

## Progress
- 已完成：D2/D4 代码实现（transport canonical 事件、ModelResponse thinking、OpenAI/OpenRouter reasoning 提取、ReAct 中间态事件发射）。
- 已完成：定向测试与全量回归，OpenSpec tasks 全部打勾。
- 待完成：提交评审与合并门禁记录补充。

## Evidence

### Commands
- `openspec new change "agentscope-d2-d4-thinking-transport"`
- `openspec status --change agentscope-d2-d4-thinking-transport --json`
- `openspec instructions apply --change "agentscope-d2-d4-thinking-transport" --json`
- `openspec validate --changes "agentscope-d2-d4-thinking-transport"`
- `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_transport_types.py tests/unit/test_transport_adapters.py tests/unit/test_openrouter_adapter.py tests/unit/test_openai_model_adapter.py tests/unit/test_react_agent_gateway_injection.py`
- `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_transport_channel.py tests/unit/test_base_agent_transport_contract.py tests/unit/test_agent_event_transport_hook.py tests/unit/test_dare_agent_hook_transport_boundary.py tests/unit/test_example_10_agentscope_compat.py`
- `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q`

### Results
- OpenSpec change 创建成功（schema: spec-driven）。
- OpenSpec apply status：`13/13 tasks complete`（state=`all_done`）。
- OpenSpec validate：`9 passed, 0 failed`（包含本 change）。
- 新增定向红绿回归：`34 passed, 1 warning`。
- 受影响面回归：`33 passed, 1 warning`。
- 全量回归：`528 passed, 12 skipped, 1 warning`。

### Behavior Verification
- Happy path:
  - `ReactAgent` 在有 `thinking_content + tool_calls` 的轮次按序发射 `thinking -> tool_call -> tool_result -> message`；
  - `ModelResponse` 保留 `thinking_content`，OpenAI/OpenRouter adapter 将 `reasoning_tokens` 归一化到 `usage`。
- Error branch:
  - transport 对无效 message/control payload 继续返回结构化错误载荷（`code/reason/resp`）；
  - 工具调用异常时，ReAct transport 发射 `error` 事件并保留 `tool_result` 失败信息。

### Risks and Rollback
- 风险：transport 事件枚举扩展可能影响历史消费者。
- 风险：不同 provider 的 thinking 字段解析口径不一致。
- 回滚：保留 legacy alias 归一化；必要时关闭 ReAct 中间态事件发射并回退到旧 `result/hook` 消费路径。

### Review and Merge Gate Links
- Review request: 待创建 PR 后补充链接。
- Merge gate: 待 CI + reviewer 通过后补充。
