## Context
- b680 consolidated config management in `dare_framework` under a dedicated manager and removed config providers from the plugin lifecycle.
- `dare_framework2` has no `core/` layer; config lives in `dare_framework2/config` with types and provider interfaces, but the provider/plugin hooks are unused.

## Goals / Non-Goals
- Goals:
  - Provide a single formal entry point for config management in `dare_framework2/config` using a `ConfigManager` that mirrors b680 behavior.
  - Keep the module layout consistent with `dare_framework2` (no `core/` package) while aligning behavior with b680.
  - Remove config-provider plugin hooks so config is not a component lifecycle concern.
  - Introduce a shared `ComponentType` location that lower-level modules can import without depending on builder.
- Non-Goals:
  - Implement new config file loaders or schema validation layers.
  - Rework plugin discovery beyond removing config-provider hooks.
  - Change runtime behavior outside config wiring and typing updates.

## Decisions
- Implement `ConfigManager` and helper functions in `dare_framework2/config/manager.py`, matching b680 semantics (layered merge, stable hash, reload).
- Move config dataclasses into `dare_framework2/config/models.py` and make `dare_framework2/config/__init__.py` the official public facade. If needed for compatibility, keep `config/types.py` as a thin re-export during the refactor.
- Remove `IConfigProvider`, `DefaultConfigProvider`, and config provider manager interfaces/no-op managers; config is passed directly to builders and contexts, not loaded via plugin lifecycle.
- Add `dare_framework2/contracts/component_type.py` and update `dare_framework2/builder/types.py` to re-export `ComponentType` so config can depend on a lower layer.

## Risks / Trade-offs
- Removing config-provider plugin hooks is a breaking API for any external plugins; mitigate by documenting the new entry point.
- Moving `ComponentType` introduces a new contracts package; mitigate by re-exporting through `dare_framework2.builder` to minimize churn.
- Dropping `config/impl` modules may break direct imports; use temporary re-exports if needed during the refactor.

## Migration Plan
- Add `ConfigManager` and models under `dare_framework2/config/` and update public facades.
- Update imports and move shared types to `dare_framework2/contracts`.
- Remove config-provider interfaces/managers and update builder exports.
- Update run-context typing and add ConfigManager unit tests.
