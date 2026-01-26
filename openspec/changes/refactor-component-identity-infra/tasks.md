## 1. Proposal Validation
- [x] 1.1 Run `openspec validate refactor-component-identity-infra --strict` and resolve all issues.

## 2. Infra Contracts
- [x] 2.1 Add `dare_framework/infra/` package.
- [x] 2.2 Move `ComponentType` into `dare_framework/infra/` and update imports.
- [x] 2.3 Add `infra.IComponent` Protocol exposing `component_type` and `name`.

## 3. Component Protocol Adoption
- [x] 3.1 Update domain Protocols (`tool`, `plan`, `hook`, `model`, `memory`, etc.) to extend `infra.IComponent`.
- [x] 3.2 Ensure each Protocol has a deterministic `component_type` value (per domain).

## 4. Config Enablement Helpers
- [x] 4.1 Add config helper APIs that accept `IComponent` instances (`is_component_enabled(...)`, `filter_enabled(...)`).

## 5. Builder + Manager Integration
- [x] 5.1 Replace builder-side config filtering call sites to use config component-based helpers (no separate `(type, name)` passing).
- [x] 5.2 Ensure “explicit injection vs manager-loaded” boundary rules remain unchanged.

## 6. Tests + Examples
- [x] 6.1 Update unit tests for new component identity requirements (`component_type`).
- [x] 6.2 Add/adjust coverage for config filtering based on `IComponent` instances.

## 7. Validation
- [x] 7.1 Run `pytest -q` and fix regressions.
