## 1. EventLog baseline implementation

- [x] 1.1 Add a canonical SQLite-backed `IEventLog` implementation under `dare_framework/event`.
- [x] 1.2 Implement deterministic hash-chain persistence (`prev_hash` / `event_hash`) and chain verification.
- [x] 1.3 Add canonical facade export and compatibility import path for the default event log implementation.

## 2. Replay and query semantics

- [x] 2.1 Implement deterministic `query(filter, limit)` behavior for `event_type` / `event_id`.
- [x] 2.2 Implement inclusive `replay(from_event_id=...)` and explicit missing-anchor failure semantics.

## 3. Verification and TODO closure

- [x] 3.1 Add failing unit tests for append/query/replay/verify/tamper scenarios.
- [x] 3.2 Implement minimal runtime code to make new tests pass.
- [x] 3.3 Run targeted regression tests for event log and event-trace bridge paths.
- [x] 3.4 Update `DG-005` status/evidence in `docs/todos/archive/2026-02-27_design_code_gap_todo.md`.
