## Context
The v3.4 config domain currently defines manager interface Protocols for tools, model adapters, planners, validators, remediators, protocol adapters, and hooks. These interfaces are domain-specific and should live alongside the domain interfaces they manage. The protocol adapter manager is a temporary exception and should sit at the package root until a dedicated protocol domain exists.

While validating the change, unit tests exposed circular imports in the `dare_framework/execution` package due to impl modules importing the kernel/types facades that re-export those same impl modules.

## Goals / Non-Goals
- Goals:
  - Place manager interfaces in their owning domain interface modules.
  - Keep `IProtocolAdapterManager` at the package root as a short-term placement.
  - Remove config-domain manager definitions and re-exports.
- Non-Goals:
  - Change manager behavior or loading rules.
  - Introduce a new protocol domain package.
  - Maintain backward-compatible imports.
  - Modify other framework versions.

## Decisions
- Define `IToolManager` in `dare_framework3_4/tool/interfaces.py`.
- Define `IModelAdapterManager` in `dare_framework3_4/model/interfaces.py`.
- Define `IPlannerManager`, `IValidatorManager`, and `IRemediatorManager` in `dare_framework3_4/plan/interfaces.py`.
- Create `dare_framework3_4/hook/interfaces.py` for `IHookManager`.
- Create `dare_framework3_4/protocol_adapter_manager.py` to host `IProtocolAdapterManager`.
- Remove `dare_framework3_4/config/interfaces.py` and stop exporting manager interfaces from `dare_framework3_4/config/__init__.py`.
- Update `dare_framework/execution/impl` modules to import protocols/models directly, and use `TYPE_CHECKING` for orchestrator type references to avoid circular imports.

## Risks / Trade-offs
- Breaking change for import paths that referenced `dare_framework3_4.config.interfaces`.
- Temporary root-level placement of `IProtocolAdapterManager` until a protocol domain is introduced.

## Migration Plan
1. Move manager Protocols into domain interface modules and add the new hook/protocol manager modules.
2. Update all `dare_framework3_4` imports to the new locations.
3. Remove the old config interfaces module and update the config facade exports.
4. Resolve `dare_framework/execution` circular imports by switching impl modules to local protocol/model imports.

## Open Questions
- None.
