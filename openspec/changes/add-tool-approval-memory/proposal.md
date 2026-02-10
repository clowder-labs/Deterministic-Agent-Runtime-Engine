# Change: Add persistent tool approval memory and interactive approval controls

## Why
High-risk tool usage currently depends only on static metadata (`requires_approval`) and does not maintain an approval memory. As a result, the runtime cannot reliably distinguish between previously approved calls and new calls, and repeated identical operations can trigger repeated manual approvals.

## What Changes
- Add a first-class tool approval subsystem with:
  - persisted approval rules (workspace + user scope),
  - session/one-shot approvals,
  - deterministic request matching (`capability`, `exact_params`, `command_prefix`).
- Add runtime approval gating in the Tool Loop before invoking approval-required capabilities.
- Add transport actions for approval operations:
  - `approvals:list`
  - `approvals:grant`
  - `approvals:deny`
  - `approvals:revoke`
- Add deterministic pending-approval state so external clients can approve/deny while a run is paused at an approval point.
- Add unit tests covering rule matching, persistence, pending approval flow, and action handler behavior.

## Impact
- Affected specs:
  - `core-runtime`
  - `transport-channel`
- Affected code:
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/builder.py`
  - `dare_framework/tool/action_handler.py`
  - `dare_framework/transport/interaction/resource_action.py`
  - `dare_framework/tool/_internal/control/*`
  - `tests/unit/*`
