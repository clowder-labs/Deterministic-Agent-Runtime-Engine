## 1. Implementation
- [ ] Add `SessionSummary` and `MilestoneSummary` models; extend `Task` and `RunResult` with session fields.
- [ ] Add `SessionContext` state holder and wire config snapshot binding at session start.
- [ ] Inject `previous_session_summary` into STM and record `session_id`/`session_summary` in `RunResult`.
- [ ] Emit `session.summary` EventLog entry and include `config_hash` in `session.start`.
- [ ] Add optional `SessionSummaryStore` (file-backed) and wire it into DareAgent.
- [ ] Update a five-layer example to demonstrate session summary handoff.

## 2. Tests
- [ ] Unit: `SessionSummary` construction from milestone results.
- [ ] Unit: `previous_session_summary` injected into STM before user input.
- [ ] Minimal integration: `RunResult` exposes `session_id` + `session_summary`.

## 3. Validation
- [ ] Run targeted tests (unit + integration).
