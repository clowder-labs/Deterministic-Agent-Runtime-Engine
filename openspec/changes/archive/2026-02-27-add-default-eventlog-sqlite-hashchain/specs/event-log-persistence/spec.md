## ADDED Requirements

### Requirement: Canonical SQLite EventLog implementation

The event domain SHALL provide a default SQLite-backed `IEventLog` implementation for canonical runtime usage.

#### Scenario: Event append persists record and hash link
- **WHEN** `append(event_type, payload)` is called
- **THEN** the event is persisted to SQLite with `event_id`, `timestamp`, `prev_hash`, and `event_hash`
- **AND** the returned value is the persisted `event_id`

### Requirement: Query API returns deterministic event slices

The default event log SHALL return events ordered by append sequence and support basic filtering.

#### Scenario: Query by event type with limit
- **WHEN** `query(filter={"event_type": "x"}, limit=n)` is called
- **THEN** only events with matching `event_type` are returned
- **AND** the result order is append-sequence ascending
- **AND** at most `n` events are returned

### Requirement: Replay returns inclusive snapshot from anchor event

The default event log SHALL replay events starting from the specified event id (inclusive).

#### Scenario: Replay from existing event id
- **WHEN** `replay(from_event_id=id0)` is called and `id0` exists
- **THEN** `RuntimeSnapshot.from_event_id` equals `id0`
- **AND** `RuntimeSnapshot.events` starts with event `id0`

#### Scenario: Replay from unknown event id fails fast
- **WHEN** `replay(from_event_id=id_missing)` is called and `id_missing` does not exist
- **THEN** the call fails with explicit error

### Requirement: Hash-chain verification detects tampering

The default event log SHALL verify full chain integrity across all persisted events.

#### Scenario: Valid chain passes verification
- **WHEN** events are appended through the public API only
- **THEN** `verify_chain()` returns `true`

#### Scenario: Tampered row fails verification
- **WHEN** a persisted row is modified so hash linkage no longer matches
- **THEN** `verify_chain()` returns `false`
