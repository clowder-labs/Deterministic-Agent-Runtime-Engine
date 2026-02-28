## 1. Artifact Alignment

- [x] 1.1 Re-scan `docs/design/Architecture.md` and locate stale hook/sandbox statements that conflict with current implementation evidence.
- [x] 1.2 Update stale statements to reflect current baseline (HookExtensionPoint integration and STM snapshot/rollback sandbox), while preserving remaining TODOs.

## 2. Verification and Traceability

- [x] 2.1 Validate wording consistency by searching for obsolete phrases (e.g., `Hooks (未接入)`, pending snapshot/rollback introduction) in Architecture doc.
- [x] 2.2 Update `docs/todos/archive/2026-02-27_design_code_gap_todo.md` to mark DG-001 as done with concrete evidence links to this change and modified files.
- [x] 2.3 Run OpenSpec strict validation for this change and ensure apply instructions report all tasks completed.
