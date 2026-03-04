## TODO Coverage

- D2-1~D2-4
- D4-1~D4-4

## 1. Transport contract and schema alignment (D2)

- [x] 1.1 Extend transport canonical event taxonomy to cover `message/tool_call/tool_result/thinking/error/status` with compatibility normalization for legacy aliases.
- [x] 1.2 Align transport payload/error schema so intermediate events and failures can be consumed consistently by CLI and channel integrations.
- [x] 1.3 Add contract-focused unit tests for transport type normalization and payload/error stability.
- [x] 1.4 Add transport sequence tests covering intermediate event ordering behavior.

## 2. Model response reasoning preservation (D4 core)

- [x] 2.1 Extend `ModelResponse` with optional `thinking_content` field and preserve backward compatibility for existing callers.
- [x] 2.2 Update OpenAI/OpenRouter adapters to extract reasoning content and normalize `reasoning_tokens` into usage metadata.
- [x] 2.3 Add adapter regression tests verifying thinking preservation and reasoning token normalization.

## 3. ReAct loop intermediate event emission (D4 execution)

- [x] 3.1 Emit `thinking` events from the execute loop when `thinking_content` is present.
- [x] 3.2 Emit `tool_call` and `tool_result` events around tool execution rounds in deterministic order.
- [x] 3.3 Add end-to-end agent/transport tests asserting ordered event sequence and non-regression of final message output.

## 4. Documentation and ledger sync

- [x] 4.1 Update TODO claim ledger statuses for this slice from `planned` to `active` and keep scope mapping aligned with this change.
- [x] 4.2 Update feature aggregation evidence for this slice with commands/results/behavior verification.
- [x] 4.3 Run targeted tests and full regression, then record evidence links before requesting review.
