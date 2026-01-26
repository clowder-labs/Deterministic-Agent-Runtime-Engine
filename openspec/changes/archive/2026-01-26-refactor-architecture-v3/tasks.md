## 1. Spec and design alignment
- [x] 1.1 Update ARCHITECTURE_COMPARISON.md with v3.3 design adjustments.
- [x] 1.2 Update OpenSpec deltas/proposal/design for v3.3 layout and ownership rules.

## 2. Sync and merge sources
- [x] 2.1 Fetch and merge the remote v3-proposal branch into the local branch.
- [x] 2.2 Merge local `dare_framework3/` and remote `dare_framework3_2/` into `dare_framework3_3/` as the v3.3 baseline.

## 3. v3.3 refactor work
- [x] 3.1 Rename `impl/` directories to `internal/` and update imports.
- [x] 3.2 Define missing kernel interfaces (config/hook/tool/event/context/security).
- [x] 3.3 Add scope/usage annotations to all interface docstrings.
- [x] 3.4 Move manager/gateway interfaces into owning domains and layers.
- [x] 3.5 Update agent wiring and domain exports to match v3.3.

## 4. Validation and docs
- [x] 4.1 Update examples and docs for v3.3 usage.
- [x] 4.2 Run `openspec validate refactor-architecture-v3 --strict`.
