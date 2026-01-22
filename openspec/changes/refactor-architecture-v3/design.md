## Context
The repository currently contains two framework variants (`dare_framework` and `dare_framework2`) with different layouts. The v3.3 proposal in `doc/design/archive/ARCHITECTURE_COMPARISON.md` fixes missing kernel interfaces (config/hook/tool), clarifies manager/gateway ownership, enforces scope annotations on interfaces, renames impl packages to internal, and removes the runtime layer. It also formalizes a mixed architecture with explicit `kernel.py` and `component.py` separation per domain and a stable public API facade at each domain package.

## Goals / Non-Goals
- Goals:
  - Introduce `dare_framework3_3/` aligned to the v3.3 architecture proposal.
  - Clarify kernel vs component boundaries via `kernel.py` and `component.py` per domain.
  - Provide a stable public API facade at each domain package.
  - Add event and hook domains with dedicated interfaces and default implementations.
  - Move shared types into the correct domain ownership.
  - Rename `impl/` directories to `internal/`.
  - Refactor `dare_framework/` and `dare_framework2/` to the v3.3 domain layout and ownership rules.
- Non-Goals:
  - Redesign runtime behavior beyond required interface moves.
  - Introduce new execution semantics unrelated to the architecture layout.

## Decisions
- Decision: Adopt a domain-first layout (no `_internal`) with per-domain public facades.
  - Rationale: Matches the v3.3 proposal and keeps domain boundaries explicit.
- Decision: Remove the runtime layer and let `BaseAgent` compose defaults directly.
  - Rationale: Simplifies component wiring and aligns with the v3.3 design.
- Decision: Add event and hook domains.
  - Rationale: Event logging and extension points are first-class kernel concerns.
- Decision: Define stable kernel interfaces in `kernel.py` for config/hook/tool/event/context/security.
  - Rationale: Kernel contracts must be explicit and stable for Layer 0 usage.
- Decision: Rename `interfaces.py` to `component.py` and enforce scope tags in interface docstrings.
  - Rationale: Clarifies stability boundaries and avoids accidental coupling.
- Decision: Rename `impl/` to `internal/` across domains.
  - Rationale: Distinguishes implementation details from interface layers.
- Decision: Move manager/gateway interfaces into their owning domains and layers.
  - Rationale: DDD ownership should be explicit and consistent.
- Decision: Move `Budget`, `ExecutionSignal`, `Event`, `HookPhase`, and `RiskLevel` to their domain types.
  - Rationale: Domain ownership is explicit and avoids cross-domain coupling.

## Risks / Trade-offs
- Large refactor risk: broad import and wiring changes may cause regressions.
- Compatibility: internal path changes will break consumers that import non-facade modules.

## Migration Plan
1. Update OpenSpec deltas to v3.3 layout, kernel interfaces, and internal rename.
2. Refactor v2 code to v3.3 layout (least fragmented base).
3. Refactor v1 code to match v3.3 ownership rules and layout conventions.
4. Scaffold `dare_framework3_3` with v3.3 domain packages and facades.
5. Rename `impl/` directories to `internal/` and update imports.
6. Update docs/examples to reflect v3.3 usage.

## Open Questions
- None.
