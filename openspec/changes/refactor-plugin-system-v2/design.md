## Context
The repo is already running on the v2 Kernel loop (`IRunLoop` + `ILoopOrchestrator`) and default Kernel implementations, but:

- HITL currently records `pause/resume` without an explicit “waiting” call.
- The extension mechanism (entrypoints) is implemented in a v1-shaped composition layer, and the v2 runtime still imports many v1-era contracts/types from `dare_framework/core/*`.

The desired end state is:
- v2 closed-loop flow is preserved and remains the primary execution path.
- Entrypoint-driven extensibility is preserved, but upgraded to v2-native groups and manager semantics.
- Legacy v1 contracts/implementations are removed (no compatibility requirement), while verification examples are adapted rather than deleted.

## Decisions

### 1) HITL waiting interface (non-blocking MVP)
- Add `IExecutionControl.wait_for_human(checkpoint_id: str, reason: str) -> None`.
- MVP implementation MUST:
  - append a WORM event (e.g. `exec.waiting_human`)
  - return immediately (non-blocking) unless a future implementation chooses to block/poll.
- Orchestrator MUST call `pause()` → `wait_for_human()` → `resume()` for `PolicyDecision.APPROVE_REQUIRED` paths:
  - `execute_plan` gate (between Plan and Execute)
  - `invoke_capability` gate (before tool invocation)

### 2) New v2 entrypoint groups
Replace v1 group names with v2-specific groups to avoid accidental mixing of v1/v2 components and to make “no compatibility” explicit.

Proposed v2 group names:
- `dare_framework.v2.tools`
- `dare_framework.v2.model_adapters`
- `dare_framework.v2.validators`
- `dare_framework.v2.planners`
- `dare_framework.v2.remediators`
- `dare_framework.v2.protocol_adapters`
- `dare_framework.v2.hooks`
- `dare_framework.v2.config_providers`
- (optional placeholders) `dare_framework.v2.memory`, `dare_framework.v2.prompt_stores`, `dare_framework.v2.skills`

### 3) Manager-driven loading rules + config
Loading semantics are defined per manager, then filtered/selected via config.

**MVP scope for this change**: managers may be implemented as no-ops initially, but the interface surface MUST exist and MUST clearly document:
- what the manager is responsible for,
- what it is NOT responsible for (to protect Kernel layering),
- how entrypoints + config would be applied in a full implementation,
- and what selection/filtering semantics are expected.

- **Model adapters**: single-select by configured component name (entrypoint name). If not configured, load none (plan-driven execution remains valid).
- **Validators**: multi-load; manager returns an ordered set:
  - discover all validators from entrypoints
  - filter via config (disabled list / allow list)
  - sort by `order` ascending
  - builder composes them into a single v2 `IValidator` (composite)
- **Tools/Hooks/Protocol adapters/etc.**: follow the same pattern (single-select vs multi-load) as defined by their respective manager; selection/filtering is config-driven.

Managers that SHOULD exist as documented interface positions (even if default is no-op):
- tools
- model adapters
- planners
- validators
- remediators
- protocol adapters
- hooks
- config providers
- optional placeholders: memory / prompt stores / skills

### 4) v2 configuration keys (minimal)
The config MUST express:
- which model adapter to use (by name)
- which validators/tools/hooks are enabled/disabled (as sets)
- any per-component config payloads (optional, opaque dicts)

This change will define a minimal schema that enables:
- `model_adapter = "<entrypoint_name>"` selection
- `validators.disabled = [...]` filtering (and optionally `validators.allow = [...]`)

### 5) Migration: remove `dare_framework/core/*` v1-only surfaces
The Kernel and v2 components must stop importing `dare_framework.core.*`. The migration is:

1. Identify “shared still-needed” types currently under `core` (e.g., evidence, risk levels, tool result/definition, model messages) and move them into v2-aligned modules.
2. Update all v2 code to import from the new locations.
3. Remove v1-only protocols/implementations:
   - `IContextAssembler` → replaced by `IContextManager`
   - `IToolRuntime` → replaced by `IToolGateway`
   - `ICheckpoint` → replaced by `IExecutionControl`
   - `IPolicyEngine` / `TrustBoundary` → replaced by `ISecurityBoundary`
   - v1 plan generator interfaces → replaced by v2 `IPlanner` / `IValidator`
4. After all callers are migrated, delete the legacy modules and update tests/examples accordingly.

## Risks / Trade-offs
- Entry point group renaming is a hard break; mitigated by explicit “v2 only” intent and updating verification examples.
- Migrating shared types touches many files; mitigated by staged refactor + tests.
- Composite validator behavior must remain deterministic and auditable; mitigated by ordering rules + event logging.
