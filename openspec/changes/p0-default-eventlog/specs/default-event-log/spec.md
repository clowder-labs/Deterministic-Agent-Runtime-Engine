## ADDED Requirements

### Requirement: Default EventLog implementation SHALL be available
The framework SHALL provide a default `IEventLog` implementation in the canonical `event` domain.

- The default implementation MUST support `append`, `query`, `replay`, and `verify_chain`.
- The default implementation MUST be usable without external services in local runtime environments.

#### Scenario: Builder can run with default event log
- **GIVEN** no explicit event log is injected by the caller
- **WHEN** runtime is built with default event logging enabled
- **THEN** a default `IEventLog` implementation is attached and receives runtime events

### Requirement: Event integrity MUST use hash-chain verification
The default event log SHALL maintain append-only integrity with a deterministic hash-chain.

- Each record MUST include `prev_hash` and `hash`.
- `verify_chain` MUST return `false` when any persisted event content is tampered with.

#### Scenario: Hash-chain verification succeeds for untampered log
- **WHEN** events are appended through normal runtime flow
- **THEN** `verify_chain` returns `true`

#### Scenario: Hash-chain verification detects tampering
- **GIVEN** an event record is modified after persistence
- **WHEN** `verify_chain` is executed
- **THEN** it returns `false`

### Requirement: Replay MUST return deterministic snapshot data
The default event log SHALL provide deterministic replay output from a given event boundary.

- `replay(from_event_id)` MUST return events in append order.
- Replay output MUST include enough state to reconstruct minimal runtime context for audit purposes.

#### Scenario: Replay returns ordered event window
- **GIVEN** a persisted event sequence with a known `from_event_id`
- **WHEN** replay is requested from that id
- **THEN** returned events are ordered by append sequence and include correlation metadata

