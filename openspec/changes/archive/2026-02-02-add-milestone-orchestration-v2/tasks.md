## 1. Types & Interfaces

- [x] 1.1 Add `Evidence` dataclass to `plan/types.py`
- [x] 1.2 Add `DecompositionResult` dataclass to `plan/types.py`
- [x] 1.3 Add `StepResult` dataclass to `plan/types.py`
- [x] 1.4 Extend `VerifyResult` with `evidence_required` / `evidence_collected` fields
- [x] 1.5 Add `decompose()` method to `IPlanner` interface with default implementation
- [x] 1.6 Add `IPlanAttemptSandbox` interface to `plan/interfaces.py`
- [x] 1.7 Add `IStepExecutor` interface to `plan/interfaces.py`
- [x] 1.8 Add `IEvidenceCollector` interface to `plan/interfaces.py`

## 2. Sandbox Implementation

- [x] 2.1 Implement `DefaultPlanAttemptSandbox` in `agent/_internal/sandbox.py`
- [ ] 2.2 Add `create_snapshot()` / `rollback()` methods to `IContext` (deferred: sandbox operates on context directly)
- [x] 2.3 Write unit tests for sandbox snapshot/rollback (inline verification)

## 3. Milestone Decomposition

- [x] 3.1 Add default `decompose` implementation in `IPlanner` interface
- [x] 3.2 Update `_run_session_loop` to call `decompose` when milestones empty
- [ ] 3.3 Add decomposition prompt template (deferred: requires LLM planner impl)
- [ ] 3.4 Write unit tests for decomposition (deferred: requires test framework setup)

## 4. Evidence Collection

- [x] 4.1 Implement `DefaultEvidenceCollector` in `agent/_internal/step_executor.py`
- [ ] 4.2 Update `_run_tool_loop` to collect evidence from tool results (deferred: requires execute loop refactor)
- [ ] 4.3 Update `MilestoneState` to store collected evidence (deferred: requires state refactor)
- [ ] 4.4 Update `verify_milestone` to check evidence against criteria (deferred: requires validator impl)
- [ ] 4.5 Write unit tests for evidence collection and validation

## 5. Step-Driven Execution

- [x] 5.1 Implement `DefaultStepExecutor` in `agent/_internal/step_executor.py`
- [x] 5.2 Add `execution_mode` config option (`step_driven` | `model_driven`)
- [ ] 5.3 Update `_run_execute_loop` to support step-driven mode (deferred: next phase)
- [ ] 5.4 Write unit tests for step-driven execution

## 6. Integration & Testing

- [x] 6.1 Update `DareAgent.__init__` to accept new components
- [ ] 6.2 Update `AgentBuilder` to support new components (deferred)
- [x] 6.3 Verify imports and type creation
- [x] 6.4 Verify DareAgent parameter integration

## Summary

**Completed in this phase:**
- All new types and interfaces
- Sandbox implementation with snapshot/rollback
- Step executor and evidence collector implementations
- DareAgent integration with new parameters
- Session loop decompose logic
- Milestone loop sandbox isolation logic

**Deferred to next phase:**
- Step-driven execution mode in execute loop
- Full evidence collection integration
- AgentBuilder updates
- Comprehensive unit tests
