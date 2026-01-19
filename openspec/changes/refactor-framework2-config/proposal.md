# Change: Refactor framework2 config management

## Why
`dare_framework2` currently exposes config types plus a config-provider plugin surface that is not wired into the runtime. The b680 change consolidated config handling into a single manager for `dare_framework`. We need the same determinism and single entry point in `dare_framework2` while honoring its module layout (no `core/` layer).

## What Changes
- Introduce `ConfigManager` under `dare_framework2/config/` to merge layered config (`system < project < user < session`), compute a deterministic config hash, and provide `get`/`get_namespace` accessors.
- Consolidate config models into a dedicated module and make `dare_framework2.config` the official public facade for `Config`, `LLMConfig`, `ComponentConfig`, and `ConfigManager`.
- Remove the config-provider plugin surface (`IConfigProvider`, `DefaultConfigProvider`, and config provider manager hooks) so config is no longer part of the component lifecycle. **BREAKING**
- Move `ComponentType` to a shared contracts module to keep config independent of builder-specific modules.
- Align tool run contexts to carry the effective `Config` snapshot.

## Impact
- Affected specs: `configuration`, `configuration-management`, `component-management`, `plugin-system`.
- Affected code: `dare_framework2/config/`, `dare_framework2/builder/`, `dare_framework2/tool/impl/run_context_state.py`, new `dare_framework2/contracts/`, tests.
