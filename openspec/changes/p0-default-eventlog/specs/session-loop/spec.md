## MODIFIED Requirements

### Requirement: Session summary emission
The runtime SHALL generate a deterministic `SessionSummary` at session end and append it to the EventLog. The `RunResult` SHALL expose `session_id` and `session_summary`.

When the default event log is enabled, session summary events MUST be persisted without requiring explicit event log injection by the caller.

#### Scenario: RunResult exposes session summary
- **WHEN** the Session Loop completes
- **THEN** the returned `RunResult` includes `session_id` and `session_summary`
- **AND** `session.summary` is appended to EventLog

#### Scenario: Session summary is persisted by default event log
- **GIVEN** runtime uses default event log wiring
- **WHEN** Session Loop completes
- **THEN** a `session.summary` event is persisted and queryable from the default store

