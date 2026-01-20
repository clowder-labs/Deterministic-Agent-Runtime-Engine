# Change: Refactor framework architecture to v3.3 (new package)

## Why
The current codebase contains two parallel frameworks (v1 and v2) with overlapping concepts and divergent layouts. The v3.3 architecture in `doc/ARCHITECTURE_COMPARISON.md` fixes missing kernel interfaces, clarifies manager/gateway ownership, enforces interface scope annotations, and renames impl packages to internal. Aligning implementations with that architecture reduces fragmentation and creates a clear migration path while introducing `dare_framework3_3` as a new package.

## What Changes
- Introduce `dare_framework3_3/` aligned to the v3.3 domain layout (agent + 10 domains).
- Remove the runtime layer; agents directly compose default components.
- Add event and hook domains with dedicated interfaces and implementations.
- Define stable kernel interfaces in each domain `kernel.py` (config/hook/tool/event/context/security).
- Rename `interfaces.py` to `component.py` and add explicit `kernel.py` interfaces per domain.
- Require interface docstrings to declare scope (Kernel/Component/Types) and usage scenarios.
- Move manager/gateway interfaces into their owning domains and layers.
- Rename `impl/` directories to `internal/` across domains.
- Move shared types to domain ownership (context/tool/event/hook/security).
- Update domain `__init__.py` exports to expose Protocols, types, and implementations without factory functions.
- Refactor `dare_framework/` and `dare_framework2/` to align with v3.3 domain layout and ownership rules.
- Update wiring, imports, examples, and docs to match the new structures.
- **BREAKING**: internal module paths and some import locations will change (runtime removal, internal rename).

## Impact
- Affected specs: `kernel-layout`, `organize-layered-structure`, `define-core-interfaces`, `define-core-models`, `interface-layer`, `define-trust-boundary`, `package-facades`, `package-initializers`.
- Affected code: `dare_framework/`, `dare_framework2/`, `dare_framework3_3/`, and relevant docs/tests/examples.
