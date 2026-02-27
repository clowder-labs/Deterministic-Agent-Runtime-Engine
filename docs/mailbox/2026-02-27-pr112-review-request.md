## Review Request: PR #112 (issue #111 follow-ups)

### Background
PR #112 started as an approval-manager fix (runtime context should not affect approval de-dup / persistence).
We extended it to close the remaining issue #111 follow-ups and to restore deterministic unit-test behavior locally.

### Design / References
- PR: #112 (branch: fix/102-leftover-approval-hygiene)
- Client CLI docs touched: client/DESIGN.md, client/README.md

### Spec Compliance Report

**Spec / source of truth**:
- Issue: #111 follow-up items (as tracked by PR title/branch)
- Design notes: client/DESIGN.md

**Check time**: 2026-02-27
**Checker**: 砚砚

| # | Requirement | Status | Code | Tests |
|---|-------------|--------|------|-------|
| 1 | Approval de-dup/persistence ignores internal runtime context | ✅ | dare_framework/tool/_internal/control/approval_manager.py | tests/unit/test_tool_approval_manager.py |
| 2 | CLI approvals grant/deny forwards optional session_id token | ✅ | client/main.py | tests/unit/test_client_cli.py |
| 3 | Unit suite stable across host env (OPENROUTER_API_KEY) | ✅ | tests/unit/test_client_cli.py | tests/unit/test_client_cli.py |
| 4 | Builder respects Config.components[TOOL].disabled while preserving injected tools | ✅ | dare_framework/agent/builder.py | tests/unit/test_builder_manager_resolution.py |
| 5 | OTel trace context extraction compatible across versions | ✅ | dare_framework/observability/_internal/event_trace_bridge.py | tests/unit/test_five_layer_agent.py |

### Edge Cases Checked
- Fake runtimes without close(): tolerated (client/main.py cleanup)
- Config disables referencing unknown tools: ignored safely (builder disables loop)
- OTel optional dependency absent: unchanged behavior (extract_trace_context returns None)

### Changed Files (High Signal)
- dare_framework/tool/_internal/control/approval_manager.py: approval de-dup/persistence normalization
- client/main.py: approvals session_id forwarding + tolerant runtime cleanup
- dare_framework/agent/builder.py: apply tool disables post-registration
- dare_framework/observability/_internal/event_trace_bridge.py: is_valid compat
- tests/unit/*: added/updated coverage for above

### Git SHAs
- Base (origin/main): cf6c66a0
- Head: 495daa07

### Tests
```
pytest -q tests/unit: 375 passed, 9 skipped
```

### Review Focus
1. builder tool disable semantics: do we agree injected tools should override config disables?
2. OpenTelemetry compat: any concern about treating is_valid as either property/method?
3. CLI runtime cleanup: acceptable to tolerate fakes without close()?

### Five-Pack
**What**: Close issue #111 follow-ups; make approvals/session-id flow testable; restore unit suite determinism.
**Why**: Prevent flaky unit behavior and ensure config/tool/trace boundaries behave as designed.
**Tradeoff**: PR scope is larger than the initial approval-manager fix.
**Open Questions**: Should we split PR #112 to reduce review surface area?
**Next Action**: Please review and approve PR #112 for merge.

