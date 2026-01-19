# Change: Refactor v2 core layout to domain packages (scheme 2)

## Why
The authoritative v2 architecture (`doc/design/Architecture_Final_Review_v2.1.md`, based on v2.0) positions `dare_framework/core/` as the Kernel (Layer 0) with stable contracts and a minimal, auditable closed-loop flow.

The current implementation is already broadly v2-aligned, but there are still structural mismatches that make the codebase harder to extend and reason about:
- Kernel default implementations are centralized under `core/defaults/`, which becomes a “catch-all” directory and weakens domain cohesion.
- There are layering leaks (Kernel defaults importing Layer 2 component contracts).
- Some data models/contracts (e.g., Envelope vs Tool Loop request payload) need re-evaluation to match the architecture document and maintain a clear trust boundary.

This change adopts “方案 2”: organize by domain packages, keep the core flow closed, and leave non-core implementations as no-op where appropriate.

## What Changes
- **Core domain packaging (方案 2)**:
  - Remove the centralized `dare_framework/core/defaults/` catch-all.
  - Re-home each Kernel default implementation into the domain package that owns the contract (context/event/tool/security/execution control/budget/run loop/orchestrator).
  - Remove stale/empty legacy directories under `dare_framework/core/` that no longer represent real packages.
- **Layering cleanup**:
  - Move `IMemory` to `dare_framework/contracts/` so Kernel defaults do not import Layer 2 packages.
  - Ensure Kernel (Layer 0) depends only on Kernel contracts + `contracts/` (shared types), not `components/`.
- **Tool Loop boundary cleanup**:
  - Split “execution boundary” (`Envelope`) from “tool invocation payload” (e.g., `ToolLoopRequest`) to resolve the current inconsistency in `doc/design/Architecture_Final_Review_v2.0.md` and make security-critical fields derivable from trusted sources.
  - Fix risk/approval derivation so model-driven tool calls cannot bypass policy by using an incorrect/default risk level.
- **Components & extensibility placeholders**:
  - Ensure every entrypoint-extensible category has a `components/<category>/` package with a documented interface and a no-op default (where needed).
  - Keep component manager implementations optional; interfaces + docstrings define selection/filtering semantics (model adapter single-select; validators multi-load + ordered + config-filtered; others defined per manager).
- **Plugin mechanism location**:
  - Move the entrypoint-based loading utilities from `dare_framework/plugins/` under `dare_framework/components/` (target: `dare_framework/components/plugin_system/`), while keeping Kernel imports clean.
- **Documentation alignment**:
  - Add `doc/design/Architecture_Final_Review_v2.1.md` (do not edit v2.0) and place architecture clarifications/adjustments there.
  - Update docs that describe directory layout and contracts (including `openspec/project.md`) to match the new package structure.

## Impact
- Affected code: `dare_framework/core/*`, `dare_framework/contracts/*`, `dare_framework/components/*`, `dare_framework/builder.py`, and plugin/loading utilities.
- Affected docs: `doc/design/Architecture_Final_Review_v2.0.md` (if we choose to resolve the Envelope inconsistency there), `openspec/project.md`, and developer architecture docs.
- **BREAKING**: internal import paths change; compatibility is explicitly out of scope for this project phase.

## References
- `doc/design/Architecture_Final_Review_v2.1.md`
- `doc/guides/Development_Constraints.md`
