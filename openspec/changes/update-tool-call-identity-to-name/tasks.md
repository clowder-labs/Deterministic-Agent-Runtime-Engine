## 1. Implementation
- [x] Update tool-definition export so `function.name` uses `ITool.name` and preserve `capability_id` for routing/observability.
- [x] Resolve tool calls by name to `capability_id` before invoking the gateway; handle unknown names clearly.
- [x] Enforce unique `ITool.name` values at registration/refresh time.
- [x] Update examples/docs to reflect tool-name-based calls.

## 2. Tests
- [x] Add tests verifying tool definitions use `ITool.name` and tool calls resolve to `capability_id`.
- [x] Add tests for duplicate tool-name rejection behavior.
