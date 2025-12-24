## Context
We are implementing the runtime main flow described in `doc/design/Architecture_Final_Review_v1.3.md` and aligning interfaces with `doc/design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md`.

## Goals / Non-Goals
- Goals:
  - Implement the full Session/Milestone/Plan/Execute/Tool flow with state management, budgets, and event logging.
  - Keep component interfaces pluggable, with stub implementations only.
- Non-Goals:
  - No concrete model/tool implementations.
  - No persistence backends or external integrations.

## Decisions
- Decision: Use a `dare_framework/` package layout mirroring the design docs and example imports.
- Decision: Implement main flow orchestration in `AgentRuntime`, with explicit pause/resume/cancel handling.

## Risks / Trade-offs
- Risk: Stub interfaces mean the flow cannot execute real tools/models yet.
  - Mitigation: Provide strict contracts and type hints so real implementations can be plugged in later.

## Migration Plan
- Create new modules without altering existing examples.
- Add exports in `dare_framework/__init__.py` for public types.

## Open Questions
- Should we introduce a default in-memory EventLog or keep interfaces only?
