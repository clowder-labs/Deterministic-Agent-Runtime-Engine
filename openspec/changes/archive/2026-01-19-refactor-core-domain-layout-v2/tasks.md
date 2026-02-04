## 1. Proposal Confirmation
- [x] 1.1 Confirm whether `dare_framework/plugins/` stays separate or moves under `dare_framework/components/`.
- [x] 1.2 Confirm packaging approach for “方案 2”:
  - Convert `core/*.py` domain modules into `core/<domain>/` packages, OR
  - Keep contract modules and move defaults to sibling files.
- [x] 1.3 Confirm the desired Tool Loop contract shape after splitting `Envelope` from invocation payload.

## 2. Implementation (apply stage)
- [x] 2.1 Remove stale/empty legacy directories under `dare_framework/core/` and other dead namespace packages (keep only real packages with `__init__.py`).
- [x] 2.2 Move Kernel default implementations out of `dare_framework/core/defaults/` into their owning domain packages; delete `core/defaults/`.
- [x] 2.3 Move `IMemory` (and other shared capability contracts as needed) into `dare_framework/contracts/` and update imports so Kernel defaults do not import Layer 2.
- [x] 2.4 Split `Envelope` boundary vs tool invocation payload (`ToolLoopRequest`); update:
  - orchestrator/tool gateway contracts,
  - validator-derived envelopes,
  - execute loop call sites,
  - and tests.
- [x] 2.5 Fix risk/approval derivation to come from capability registry for both plan-driven and model-driven execution paths.
- [x] 2.6 Add missing placeholder component packages/interfaces (e.g., prompt store, MCP client) with no-op defaults and clear docstrings.
- [x] 2.7 Update docs (`openspec/project.md`, architecture overview docs, and `docs/design/archive/Architecture_Final_Review_v2.1.md`) to match the new layout and updated contracts.

## 3. Validation
- [x] 3.1 Run `openspec validate refactor-core-domain-layout-v2 --strict` and fix all issues.
- [x] 3.2 Run `pytest -q` and fix regressions introduced by the refactor.
