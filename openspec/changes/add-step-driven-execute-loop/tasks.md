## 1. Spec and test scaffolding

- [x] 1.1 Add/extend unit tests that fail when `step_driven` mode does not execute `ValidatedPlan.steps` through `IStepExecutor`.
- [x] 1.2 Add/extend unit tests that fail when builder does not expose execution-mode and step-executor wiring.
- [x] 1.3 Add non-regression test proving default model-driven path still works when execution mode is not configured.

## 2. Runtime implementation

- [x] 2.1 Implement mode-based branching in `DareAgent._run_execute_loop(...)` for `model_driven` vs `step_driven`.
- [x] 2.2 Implement strict step-driven precondition handling (missing plan / unsuccessful plan / empty steps).
- [x] 2.3 Implement step execution loop using `IStepExecutor.execute_step(...)` and collect outputs/errors consistently.

## 3. Builder implementation

- [x] 3.1 Add `DareAgentBuilder.with_execution_mode(...)` API with validation and default-safe behavior.
- [x] 3.2 Add `DareAgentBuilder.with_step_executor(...)` API and pass-through wiring into `DareAgent`.
- [x] 3.3 Ensure existing builder flows remain backward compatible and preserve default model-driven runtime.

## 4. Verification and closeout

- [x] 4.1 Run targeted unit tests for DareAgent execute loop and builder wiring changes.
- [x] 4.2 Mark all completed tasks in this file and confirm OpenSpec apply status is unblocked.
- [x] 4.3 Update TODO evidence (`DG-002`, `DG-003`) with implemented change references.
