# Change: Add Session Loop Lifecycle (In-Run) + Session Summary

## Why
The current Session Loop only sequences milestones and logs start/complete events. It does not bind an effective config snapshot, does not surface a session summary, and does not accept a prior session summary for continuity. This limits auditability and makes “continue within the next run” workflows opaque.

## What Changes
- Add SessionLoop-focused models: `SessionContext`, `SessionSummary`, and `MilestoneSummary`.
- Extend `Task` to accept `previous_session_summary` (and a reserved `resume_from_checkpoint`).
- Extend `RunResult` to return `session_id` and `session_summary`.
- Bind effective config snapshot to SessionContext at session start (via ConfigProvider) and expose it to runtime components.
- Generate a deterministic SessionSummary at session end and write it to EventLog.
- Optional file persistence for SessionSummary (opt-in).
- Update a five-layer example to demonstrate session summary handoff.
- Add minimal unit coverage for summary generation and previous summary injection.

## Impact
- Affected specs: new `session-loop` capability (plus alignment with existing core-runtime/config specs).
- Affected code: `dare_framework/agent/_internal/five_layer.py`, `dare_framework/agent/_internal/orchestration.py`, `dare_framework/plan/types.py`, `dare_framework/context/_internal/context.py` (config snapshot propagation), example and tests.
- Compatibility: additive API fields on Task/RunResult; no breaking change expected.

## Notes / Constraints
- Scope is limited to in-run lifecycle management. Cross-run resume/replay is not implemented in this change.
- Optional persistence is best-effort and only used when explicitly configured.
