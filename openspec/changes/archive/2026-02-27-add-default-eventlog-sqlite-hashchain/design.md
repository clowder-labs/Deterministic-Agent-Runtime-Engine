## Context

`dare_framework/event` currently exposes only the `IEventLog` protocol and domain types. In canonical runtime, this means teams must build their own persistence backend before they can rely on replay or chain verification. Legacy event log code referenced by archived tests is not part of the canonical package surface, so `DG-005` requires a first-party baseline implementation in the event domain itself.

The required baseline is intentionally minimal but production-usable for single-process deployments: file-backed SQLite persistence, append-only semantics, hash-link integrity, replay from a known event, and chain verification.

## Goals / Non-Goals

**Goals:**
- Provide a canonical SQLite-backed `IEventLog` implementation under `dare_framework/event`.
- Persist every event with deterministic hash-chain fields (`prev_hash`, `event_hash`).
- Implement `append/query/replay/verify_chain` with stable ordering and clear edge semantics.
- Keep compatibility with existing event types (`Event`, `RuntimeSnapshot`) and observability bridge (`TraceAwareEventLog`).
- Expose the implementation through canonical facade and compatibility import path.

**Non-Goals:**
- No distributed or multi-writer consensus model.
- No event streaming transport, retention policy engine, or archival tiers.
- No taxonomy redesign for all runtime event payloads in this change.

## Decisions

### Decision 1: Use single-file SQLite with explicit event sequence

- Create table `events` with columns:
  - `seq INTEGER PRIMARY KEY AUTOINCREMENT`
  - `event_id TEXT UNIQUE NOT NULL`
  - `event_type TEXT NOT NULL`
  - `payload_json TEXT NOT NULL`
  - `timestamp_iso TEXT NOT NULL`
  - `prev_hash TEXT`
  - `event_hash TEXT NOT NULL`
- Query and replay sort by `seq ASC` to guarantee deterministic order.

Rationale:
- `seq` avoids ambiguity when timestamps are equal.
- SQLite file storage is zero-dependency and suitable as baseline default.

### Decision 2: Deterministic hash-chain over canonical payload serialization

- Canonical serialization:
  - `payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`
- Event hash input string includes: `event_id`, `event_type`, `timestamp_iso`, `payload_json`, `prev_hash`.
- Hash algorithm: SHA-256 hex digest.

Rationale:
- Stable serialization makes hash reproducible across verify passes.
- Including `event_id` and timestamp prevents hash collisions for same payload.

### Decision 3: Async interface backed by synchronous SQLite guarded by lock

- Implementation remains synchronous internally (`sqlite3`), but public methods stay async per `IEventLog`.
- Use an internal `asyncio.Lock` around DB operations to enforce in-process write/read consistency.

Rationale:
- Minimal complexity while matching existing protocol.
- Avoids race conditions under concurrent `append()` calls in one runtime process.

### Decision 4: Replay and filter semantics are strict and explicit

- `replay(from_event_id=...)` returns events starting at the specified id (inclusive).
- If `from_event_id` is unknown, raise `ValueError`.
- `query(filter=..., limit=...)` supports key filters for `event_type` and `event_id`; unknown filter keys are ignored in baseline.

Rationale:
- Inclusive replay maps directly to audit workflows.
- Explicit unknown-id failure avoids silent partial replay.

## Risks / Trade-offs

- [Risk] SQLite backend is not ideal for high-throughput distributed writes.  
  -> Mitigation: document this as baseline implementation and keep `IEventLog` pluggable.

- [Risk] Payload canonicalization may diverge if non-JSON-serializable values are emitted.  
  -> Mitigation: fail fast on serialization error and surface actionable exception.

- [Risk] Hash verification only proves local file integrity, not external tamper-proof storage.  
  -> Mitigation: keep interface open for stronger backends (WORM store, external signer).

## Migration Plan

1. Add SQLite event log implementation under `dare_framework/event/_internal`.
2. Add canonical and compatibility exports.
3. Add/port unit tests for append/query/replay/verify/tamper detection.
4. Run targeted tests and update `DG-005` TODO evidence.

Rollback:
- Revert new event log implementation and exports; interface-only mode remains unchanged.

## Open Questions

- Should baseline implementation include optional periodic compaction/checkpoint behavior?
- Do we need standardized query filtering for payload nested fields in the next iteration?
