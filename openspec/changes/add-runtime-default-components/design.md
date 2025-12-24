## Context
The runtime orchestration requires concrete component implementations for local testing and example usage. These defaults must be minimal and safe while keeping the interface contract intact.

## Goals / Non-Goals
- Goals:
  - Provide deterministic, no-op or minimal implementations for core components.
  - Keep implementations dependency-free and suitable for tests.
- Non-Goals:
  - Production-grade persistence or external integrations.
  - Full LLM or tool execution capabilities.

## Decisions
- Decision: Implement in-memory/no-op components (e.g., list-backed EventLog, in-memory Checkpoint).
- Decision: Keep validators permissive with explicit defaults so runtime flow can complete.

## Risks / Trade-offs
- Risk: Defaults may mask missing real integrations in production.
  - Mitigation: Name implementations clearly (e.g., `InMemoryEventLog`, `NoopModelAdapter`) and document as non-production.

## Migration Plan
- Add new modules without altering existing runtime interfaces.
- Export defaults for use in examples and tests.

## Open Questions
- Should any default implementation be excluded from public exports?
