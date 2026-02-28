## 1. Default assemble fusion behavior

- [x] 1.1 Implement default STM/LTM/Knowledge fusion in `DefaultAssembledContext.assemble`.
- [x] 1.2 Add query-derivation logic based on latest user intent in STM.
- [x] 1.3 Add retrieval metadata fields for counts/query/degradation state.

## 2. Budget-aware degradation semantics

- [x] 2.1 Add lightweight token estimation and remaining-budget calculation for assemble path.
- [x] 2.2 Implement deterministic degradation policy (reduce/skip LTM & Knowledge under low budget).
- [x] 2.3 Ensure retrieval-source exceptions degrade gracefully without failing assemble.

## 3. Verification and TODO closure

- [x] 3.1 Add failing unit tests for fusion order, query derivation, and low-budget degradation.
- [x] 3.2 Implement minimal code changes to make new tests pass.
- [x] 3.3 Run targeted regressions for context assembly and impacted agent execution paths.
- [x] 3.4 Update `DG-006` status/evidence in `docs/todos/archive/2026-02-27_design_code_gap_todo.md`.
