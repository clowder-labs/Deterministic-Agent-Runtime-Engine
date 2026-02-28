## Context

`DareAgent` currently accepts `execution_mode` and `step_executor` parameters, but the Execute Loop always follows model-driven behavior. This creates a drift between runtime contracts and actual behavior: validated plan steps are produced by validators but not consumed by a dedicated step-driven path. In parallel, `DareAgentBuilder` does not expose explicit APIs for execution-mode and step-executor wiring, so callers cannot deterministically assemble this behavior from the public builder surface.

The change must preserve default behavior (model-driven execution) while introducing a deterministic step-driven path for validated plans. It must also remain compatible with existing planner/validator/remediator integrations and avoid introducing breaking changes to existing builder flows.

## Goals / Non-Goals

**Goals:**
- Add an explicit step-driven execution path in `DareAgent` that executes `ValidatedPlan.steps` sequentially via `IStepExecutor`.
- Keep model-driven execution as default and preserve existing behavior when step-driven mode is not configured.
- Expose builder APIs to configure execution mode and custom step executor deterministically.
- Add focused tests that demonstrate new behavior and non-regression of default path.

**Non-Goals:**
- No redesign of planner/validator interfaces.
- No changes to security boundary integration in this change.
- No change to tool gateway envelope semantics beyond consuming existing validated step data.

## Decisions

### Decision 1: Branch Execute Loop by configured mode

- Add a mode switch in `DareAgent._run_execute_loop(...)`.
- `model_driven` keeps current loop unchanged.
- `step_driven` requires a validated plan with steps and executes them using `IStepExecutor`.

Alternatives considered:
- Infer mode automatically from presence of steps.
  - Rejected: implicit behavior is hard to reason about and can create surprising runtime switching.

### Decision 2: Fail fast on invalid step-driven prerequisites

- In `step_driven` mode:
  - If `plan is None`, return failure with explicit error.
  - If `plan.success is False`, return failure with explicit error.
  - If `plan.steps` is empty, return failure with explicit error.
- This keeps contract strict and debuggable.

Alternatives considered:
- Silent fallback to model-driven.
  - Rejected: masks configuration errors and weakens deterministic execution guarantees.

### Decision 3: Provide builder-level explicit configuration

- Add `DareAgentBuilder.with_execution_mode(execution_mode)` and `DareAgentBuilder.with_step_executor(step_executor)`.
- Keep default `execution_mode="model_driven"` and `step_executor=None`.

Alternatives considered:
- Configure only via `Config`.
  - Rejected: lacks explicit per-builder control and is less direct for tests/examples.

## Risks / Trade-offs

- [Risk] Step-driven mode returns failures when plan data is missing, which may surprise users expecting implicit fallback.  
  → Mitigation: keep default mode model-driven and document strict prerequisites in tests and change artifacts.

- [Risk] Mode branching can introduce regressions to existing execute loop behavior.  
  → Mitigation: add non-regression tests proving default model-driven path remains unchanged.

- [Risk] Custom step executors may produce inconsistent output formats.  
  → Mitigation: normalize outputs in `StepResult` handling and cover expected shape in unit tests.

## Migration Plan

1. Add spec deltas for plan-module and component-management.
2. Add failing tests for step-driven execution and builder wiring.
3. Implement minimal runtime and builder changes to satisfy tests.
4. Run targeted unit tests.
5. Update docs/TODO status references after verification.

Rollback strategy:
- Revert this change to restore model-driven-only behavior (no data migration required).

## Open Questions

- Should step-driven mode support optional fallback to model-driven behind an explicit flag in a future change?
- Should builder mode selection also be reflected in Config-level defaults for CLI assembly paths?
