## Overview
This change introduces a small cross-domain `infra` package to centralize component identity contracts that are referenced by config, managers, and builders.

The goal is to:
1) Make component type explicit and typed for every pluggable interface.
2) Allow config enable/disable filtering to operate on components directly (passing a component object), instead of requiring call sites to pass `(ComponentType, name)` and duplicate name-resolution logic.

## Key Decisions
### 1) `infra` as the home for shared identity contracts
`ComponentType` and the base `IComponent` identity Protocol live under `dare_framework/infra/` so all domains can import them without creating an artificial dependency on the config domain.

This aligns with the “cross-layer shared type” intent previously expressed via the legacy `contracts/` module.

### 2) Component Protocols expose both `component_type` and `name`
Config enable/disable and per-component configuration are name-based. To make filtering deterministic and avoid duplicating name-resolution logic, this change standardizes two required identity fields on every pluggable interface:

- `component_type: ComponentType`
- `name: str`

If an implementation wants to use the class name for config lookup, it SHOULD implement `name` accordingly (e.g., returning `self.__class__.__name__`).

### 3) Config APIs accept components directly
Config remains a frozen, JSON-derived model. This change only adds helper APIs that accept `IComponent` instances for enablement checks and filtering, so call sites can remain simple:

- `Config.is_component_enabled(component: IComponent) -> bool`
- `Config.filter_enabled(components: Sequence[IComponent]) -> list[IComponent]`

## Migration Notes (apply stage)
- Update all domain component Protocols (`ITool`, `IValidator`, `IHook`, `IPlanner`, `IModelAdapter`, etc.) to extend `infra.IComponent` and expose `component_type` + `name`.
- Move `ComponentType` import sites to `dare_framework.infra`.
- Replace builder-side filtering helpers that require `(type, obj)` with config methods that accept the component directly.
