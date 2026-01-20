## Context
The repository currently contains two framework variants (`dare_framework` and `dare_framework2`) with different layouts. The v3.2 proposal in `doc/ARCHITECTURE_COMPARISON.md` specifies domain ownership fixes (context/memory, security), removes the runtime layer, and adds event/hook domains. It also formalizes a mixed architecture with explicit `kernel.py` and `component.py` separation per domain and a stable public API facade at each domain package.

## Goals / Non-Goals
- Goals:
  - Introduce `dare_framework3/` aligned to the v3.2 architecture proposal.
  - Clarify kernel vs component boundaries via `kernel.py` and `component.py` per domain.
  - Provide a stable public API facade at each domain package.
  - Add event and hook domains with dedicated interfaces and default implementations.
  - Move shared types into the correct domain ownership.
  - Refactor `dare_framework/` and `dare_framework2/` to the v3.2 domain layout and ownership rules.
- Non-Goals:
  - Redesign runtime behavior beyond required interface moves.
  - Introduce new execution semantics unrelated to the architecture layout.

## Decisions
- Decision: Adopt a domain-first layout (no `_internal`) with per-domain public facades.
  - Rationale: Matches the v3.2 proposal and keeps domain boundaries explicit.
- Decision: Remove the runtime layer and let `BaseAgent` compose defaults directly.
  - Rationale: Simplifies component wiring and aligns with the v3.2 design.
- Decision: Add event and hook domains.
  - Rationale: Event logging and extension points are first-class kernel concerns.
- Decision: Rename `interfaces.py` to `component.py` and add empty `kernel.py` placeholders.
  - Rationale: Clarifies stability boundaries for evolving interfaces.
- Decision: Move `Budget`, `ExecutionSignal`, `Event`, `HookPhase`, and `RiskLevel` to their domain types.
  - Rationale: Domain ownership is explicit and avoids cross-domain coupling.

## Risks / Trade-offs
- Large refactor risk: broad import and wiring changes may cause regressions.
- Compatibility: internal path changes will break consumers that import non-facade modules.

## Migration Plan
1. Update OpenSpec deltas to v3.2 layout and type ownership.
2. Refactor v2 code to v3.2 layout (least fragmented base).
3. Refactor v1 code to match v3.2 ownership rules and layout conventions.
4. Scaffold `dare_framework3` with v3.2 domain packages and facades.
5. Update docs/examples to reflect v3.2 usage.

## Open Questions
- None.
