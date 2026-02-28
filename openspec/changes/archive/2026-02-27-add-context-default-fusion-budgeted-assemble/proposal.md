## Why

Default `Context.assemble()` currently uses STM only, so LTM/Knowledge retrieval is not part of the canonical baseline and context quality degrades for multi-step tasks. This leaves `DG-006` unresolved and keeps architecture claims ahead of implementation.

## What Changes

- Implement a default STM/LTM/Knowledge fusion path in `DefaultAssembledContext`.
- Derive retrieval query from latest user intent in STM.
- Add budget-aware degradation semantics: under low remaining token budget, reduce or skip LTM/Knowledge retrieval before model call.
- Emit retrieval metadata (`query`, source counts, degradation reason) in `AssembledContext.metadata`.
- Add unit tests for fusion order, query derivation, and budget degradation behavior.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `chat-runtime`: default context assembly behavior changes from STM-only to fused retrieval with budget-aware fallback.

## Impact

- Affected code:
  - `dare_framework/context/context.py`
  - `tests/unit/test_context_implementation.py`
- API impact:
  - No breaking signature changes to `IContext` / `AssembledContext`.
- Behavior impact:
  - Runtime receives richer default context and explicit degradation metadata when budget is constrained.
