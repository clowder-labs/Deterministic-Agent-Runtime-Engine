# Design: Session Loop Lifecycle (In-Run) + Session Summary

## Goals
- Provide a concrete Session Loop lifecycle within a single run.
- Bind an effective Config snapshot to SessionContext at session start.
- Accept a prior SessionSummary and inject it into the session context.
- Emit a deterministic SessionSummary and write it to EventLog.
- Keep the change minimal, additive, and opt-in for persistence.

## Non-Goals
- Cross-run resume/replay via checkpoint or event replay.
- Multi-session selection policies or long-term session stores.
- LLM-generated summaries (summary is deterministic from runtime state).

## Proposed Data Models

### SessionContext
Location: `dare_framework/agent/_internal/orchestration.py`

Fields:
- `session_id: str`
- `task_id: str`
- `config: Config | None` (effective snapshot)
- `config_hash: str | None` (sha256 of `config.to_dict()` for audit)
- `previous_session_summary: SessionSummary | None`
- `milestone_summaries: list[MilestoneSummary]` (populated at end)

Rationale: Keep session-specific runtime metadata in one place and avoid overloading Context with non-context metadata.

### MilestoneSummary
Location: `dare_framework/plan/types.py` (plan domain owns milestones)

Fields:
- `milestone_id: str`
- `description: str`
- `attempts: int`
- `success: bool`
- `outputs: list[Any]`
- `errors: list[str]`
- `evidence_count: int`
- `reflections_count: int`

### SessionSummary
Location: `dare_framework/plan/types.py`

Fields:
- `session_id: str`
- `task_id: str`
- `success: bool`
- `started_at: float`
- `ended_at: float`
- `duration_ms: float`
- `milestones: list[MilestoneSummary]`
- `final_output: Any | None`
- `errors: list[str]`
- `metadata: dict[str, Any]`

Deterministic generation from runtime state ensures auditability and avoids LLM dependency.

## Session Loop Flow (In-Run)

1. **Session init**
   - Ensure `SessionState` exists (session_id == run_id).
   - Create `SessionContext` and attach it to the agent runtime.
   - Resolve effective config snapshot via `IConfigProvider.current()` if provided.
   - Compute `config_hash` for EventLog.
   - Apply config snapshot to runtime Context: `context.config_update(config.to_dict())`.

2. **Previous session summary injection**
   - If `Task.previous_session_summary` is provided, store it on SessionContext.
   - Inject a summary message into STM before the user task message.
   - Message format (deterministic):
     - role: `system`
     - content: `"Previous session summary (session_id=...): <summary-json>"`
   - This supports within-run continuation without cross-run replay.

3. **Milestone execution**
   - Run milestone loop sequentially as today.
   - Track milestone attempts, evidence count, and errors for summary construction.

4. **Session finalization**
   - Build `MilestoneSummary` entries from `MilestoneState` and `MilestoneResult`.
   - Build `SessionSummary` with duration and final output.
   - Emit `session.summary` EventLog entry (payload includes summary dict + `config_hash`).
   - Include `session_id` and `session_summary` in `RunResult`.

## EventLog Semantics
- `session.start`: includes `task_id`, `session_id`, `config_hash`, `has_previous_summary`.
- `session.complete`: includes `task_id`, `session_id`, `success`, `duration_ms`.
- `session.summary`: includes `task_id`, `session_id`, and serialized `SessionSummary`.

All events preserve the existing correlation fields already injected by `_log_event`.

## Optional Persistence
- Provide an optional `SessionSummaryStore` interface or callback (e.g., `session_summary_store.save(summary)`), injected into DareAgent.
- Default: None (no persistence beyond EventLog).
- Optional file-backed implementation writes JSON to `.dare/<agent_name>/session_summaries/<session_id>.json`.

## API Changes
- `Task` gains:
  - `previous_session_summary: SessionSummary | None`
  - `resume_from_checkpoint: str | None` (reserved; ignored for now)
- `RunResult` gains:
  - `session_id: str | None`
  - `session_summary: SessionSummary | None`

These changes are additive and backward compatible.

## Example Update
- Update a five-layer example (e.g., `examples/04-dare-coding-agent`) to:
  - Run once, capture `RunResult.session_summary`.
  - Run a follow-up task with `previous_session_summary` populated.
  - Print the session summary and demonstrate continuity.

## Testing Strategy
- Unit test: `SessionSummary` generation from milestone results/states.
- Unit test: `Task.previous_session_summary` is injected into STM.
- Optional integration test: simple five-layer agent returns `RunResult.session_summary` with expected fields.

## Risks and Mitigations
- **Large summary payloads**: keep summary deterministic and compact; do not include full message history.
- **Config snapshot size**: store hash in EventLog and keep full config in SessionContext only.
- **Optional persistence**: only enabled when explicitly configured.

## Compatibility Notes
- Existing code paths that construct `Task` without new fields remain valid.
- EventLog remains optional; summary logging is best-effort if configured.
