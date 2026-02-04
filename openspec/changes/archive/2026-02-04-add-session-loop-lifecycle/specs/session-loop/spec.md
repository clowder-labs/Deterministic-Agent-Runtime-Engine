# session-loop Specification (Delta)

## ADDED Requirements

### Requirement: SessionContext initialization and config snapshot
The runtime SHALL create a SessionContext at the start of a session and bind the effective Config snapshot (if a ConfigProvider is supplied). The session start event SHALL include a `config_hash` derived from the snapshot.

#### Scenario: Session context includes config snapshot
- **GIVEN** a runtime configured with an `IConfigProvider`
- **WHEN** a session starts
- **THEN** SessionContext stores the effective Config snapshot
- **AND** `session.start` includes `config_hash`

### Requirement: Previous session summary handoff
The runtime SHALL accept `Task.previous_session_summary` and attach it to SessionContext, and SHALL inject a deterministic summary message into STM before the current user input.

#### Scenario: Summary is injected into context
- **GIVEN** a Task with `previous_session_summary`
- **WHEN** the Session Loop initializes
- **THEN** STM contains a summary message ahead of the current user message

### Requirement: Session summary emission
The runtime SHALL generate a deterministic `SessionSummary` at session end and append it to the EventLog. The `RunResult` SHALL expose `session_id` and `session_summary`.

#### Scenario: RunResult exposes session summary
- **WHEN** the Session Loop completes
- **THEN** the returned `RunResult` includes `session_id` and `session_summary`
- **AND** `session.summary` is appended to EventLog

### Requirement: Optional summary persistence
If a SessionSummary store/sink is configured, the runtime SHALL persist the summary after session completion. If not configured, no persistence is performed.

#### Scenario: Summary store is configured
- **GIVEN** a session summary store is configured
- **WHEN** a session completes
- **THEN** the summary is persisted via the store

### Requirement: Reserved resume_from_checkpoint input
`Task` SHALL accept a `resume_from_checkpoint` field for future resume workflows. The current runtime MAY ignore it.

#### Scenario: Reserved field is accepted
- **GIVEN** a Task with `resume_from_checkpoint` set
- **WHEN** the runtime runs the session
- **THEN** the session proceeds without error even if resume is not implemented
