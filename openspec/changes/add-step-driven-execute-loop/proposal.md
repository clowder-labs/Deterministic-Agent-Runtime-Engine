## Why

`DareAgent` already exposes `execution_mode` and `step_executor` construction parameters, but runtime execution still follows a model-driven path only. This creates a contract gap: validated plan steps are not consistently executable as first-class runtime behavior, and builder APIs cannot assemble step-driven execution deterministically.

## What Changes

- Add a true step-driven Execute Loop path in `DareAgent` that consumes `ValidatedPlan.steps` sequentially via `IStepExecutor`.
- Keep model-driven execution as the default path and enforce explicit fallback semantics when a plan is absent or invalid.
- Extend `DareAgentBuilder` with explicit `with_execution_mode(...)` and `with_step_executor(...)` APIs so step-driven mode can be assembled intentionally.
- Add regression tests that prove:
  - step-driven mode executes validated steps through `IStepExecutor`
  - builder wiring passes execution mode and step executor into `DareAgent`
  - model-driven mode remains unchanged by default
- Update design artifacts to align with actual runtime behavior and remove the current implementation gap claim.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `plan-module`: Execute Loop must support step-driven execution that consumes `ValidatedPlan.steps`.
- `component-management`: DareAgent builder must expose deterministic configuration for execution mode and step executor wiring.

## Impact

- Affected code:
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/builder.py`
  - `dare_framework/agent/_internal/step_executor.py` (integration path only)
  - `tests/unit/**` (new/updated tests for execution mode behavior)
- API impact:
  - Additive builder API only (`with_execution_mode`, `with_step_executor`), no breaking removals.
- Runtime behavior:
  - Optional new execution path when explicitly configured; default behavior remains model-driven.
