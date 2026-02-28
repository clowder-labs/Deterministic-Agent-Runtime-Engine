## Why

`IEventLog` is currently interface-only in the canonical runtime, so audit persistence, replay, and chain verification are not available out of the box. This makes compliance and deterministic post-mortem analysis harder than necessary.

## What Changes

- Add a canonical SQLite-backed `IEventLog` default implementation with append-only semantics.
- Persist hash-chain fields (`prev_hash`, `event_hash`) for each event and verify integrity via `verify_chain()`.
- Implement `query(...)` and `replay(...)` against persisted rows with deterministic ordering.
- Export the default implementation from the event domain facade and provide compatibility import path.
- Add focused unit tests for append/query/replay/verify/tamper scenarios.

## Capabilities

### New Capabilities
- `event-log-persistence`: Provide a production-usable baseline event log implementation (`sqlite + hash-chain + replay + verify`) for canonical `dare_framework/event`.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `dare_framework/event/**`
  - `tests/unit/test_event_*`
  - optional builder wiring in `dare_framework/agent/builder.py` (if convenience API is added)
- API impact:
  - Additive: new default event log class export and compatibility path.
- Behavior impact:
  - Event persistence can be enabled with a first-party implementation and audited with chain verification.
