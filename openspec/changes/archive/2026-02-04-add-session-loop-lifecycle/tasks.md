## 1. Implementation
- [x] Add `SessionSummary` and `MilestoneSummary` models; extend `Task` and `RunResult` with session fields.
- [x] Add `SessionContext` state holder and wire config snapshot binding at session start.
- [x] Inject `previous_session_summary` into STM and record `session_id`/`session_summary` in `RunResult`.
- [x] Emit `session.summary` EventLog entry and include `config_hash` in `session.start`.
- [x] Add optional `SessionSummaryStore` (file-backed) and wire it into DareAgent.
- [x] Update a five-layer example to demonstrate session summary handoff.

## 2. Tests
- [x] Unit: `SessionSummary` construction from milestone results.
- [x] Unit: `previous_session_summary` injected into STM before user input.
- [x] Minimal integration: `RunResult` exposes `session_id` + `session_summary`.

## 3. Validation
- [x] Run targeted tests (unit + integration).
