# Change: Refactor framework architecture to v3.2 (new package)

## Why
The current codebase contains two parallel frameworks (v1 and v2) with overlapping concepts and divergent layouts. The v3.2 architecture in `doc/ARCHITECTURE_COMPARISON.md` clarifies kernel boundaries, fixes domain ownership (context/memory, security), removes the runtime layer, and introduces event/hook domains. Aligning implementations with that architecture reduces fragmentation and creates a clear migration path while introducing `dare_framework3` as a new package.

## What Changes
- Introduce `dare_framework3/` aligned to the v3.2 domain layout (agent + 10 domains).
- Remove the runtime layer; agents directly compose default components.
- Add event and hook domains with dedicated interfaces and implementations.
- Rename `interfaces.py` to `component.py` and add empty `kernel.py` placeholders per domain.
- Move shared types to domain ownership (context/tool/event/hook/security).
- Update domain `__init__.py` exports to expose Protocols, types, and implementations without factory functions.
- Refactor `dare_framework/` and `dare_framework2/` to align with v3.2 domain layout and ownership rules.
- Update builder wiring, imports, examples, and docs to match the new structures.
- **BREAKING**: internal module paths and some import locations will change (runtime removal, facade packages removed).

## Impact
- Affected specs: `kernel-layout`, `organize-layered-structure`, `define-core-interfaces`, `define-core-models`, `interface-layer`, `define-trust-boundary`, `package-facades`, `package-initializers`.
- Affected code: `dare_framework/`, `dare_framework2/`, `dare_framework3/`, and relevant docs/tests/examples.
