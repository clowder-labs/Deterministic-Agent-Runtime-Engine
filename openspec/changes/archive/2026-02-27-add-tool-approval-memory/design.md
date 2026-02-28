## Context
We need a production-grade approval capability similar to mature coding agents: once a user has approved a matching tool invocation policy, equivalent future calls should pass without repeated prompts. The runtime already exposes deterministic action/control channels and trusted tool metadata, which provides a natural integration point.

## Goals / Non-Goals
- Goals:
  - Persist approval decisions and reuse them safely.
  - Support multiple approval scopes (once/session/workspace/user).
  - Block approval-required tools until explicit grant/deny when no rule matches.
  - Keep approval matching deterministic and auditable.
- Non-Goals:
  - Natural-language policy authoring.
  - Cross-workspace distributed approval synchronization.

## Decisions
- Decision: Introduce a dedicated `ToolApprovalManager` in tool control internals.
  - Why: keeps policy state near execution control and avoids leaking approval logic into tool implementations.
- Decision: Use layered rule stores.
  - Workspace store: `.dare/approvals.json` under `workspace_dir`.
  - User store: `.dare/approvals.json` under `user_dir`.
  - Session and one-shot scopes remain in-memory.
- Decision: Deterministic matcher strategies.
  - `capability`: approve/deny by capability id.
  - `exact_params`: canonical JSON hash match.
  - `command_prefix`: prefix match for `command` parameter.
- Decision: Tool loop waits on pending approval.
  - Approval-required calls without matching rule create pending requests and await resolution from transport action handlers.

## Risks / Trade-offs
- Risk: Over-broad rules can allow too much.
  - Mitigation: default grant mode is `exact_params`; `command_prefix` and `capability` must be explicit.
- Risk: Blocking waits may stall runs if no client responds.
  - Mitigation: keep deterministic pending list accessible via `approvals:list` for observability and control.

## Migration Plan
1. Add approval manager/models/stores and unit tests.
2. Wire approval manager into builder and agent runtime.
3. Add interaction actions and handlers for approval operations.
4. Validate with targeted unit tests and strict OpenSpec validation.

## Open Questions
- Should future versions support explicit TTL expiration in action payloads? (designed to be extendable but not required for this change)
