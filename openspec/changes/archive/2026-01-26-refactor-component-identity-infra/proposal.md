# Change: Refactor component identity into infra

## Why
Component enable/disable and per-component configuration are currently name-based, but component identity is spread across domains and does not have a single canonical contract. This makes config filtering brittle (different components expose different identity attributes) and forces builder/runtime code to re-implement “name parsing” in multiple places.

## What Changes
- Introduce an `infra` module for cross-domain shared component identity contracts.
- Move `ComponentType` into `infra` and make component interfaces expose deterministic component identity (`component_type` + `name`).
- Update config-facing APIs to accept `Component` instances (not `(type, name)` tuples) for enable/disable and filtering.
- Remove call-site name parsing: config reads `component.name` directly.

## Impact
- Affected specs: `core-config`, `configuration-management`, `interface-layer`, `organize-layered-structure`.
- Affected code (apply stage): component Protocols across domains, config helpers, builder config filtering call sites, tests/examples.
- **Potential BREAKING**: import path for `ComponentType` and component Protocol inheritance surface.

## Open Questions
- None.
