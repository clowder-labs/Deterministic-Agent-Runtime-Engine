# Change: Move manager interfaces to domain packages

## Why
The config domain currently hosts manager interface Protocols that belong to the tool/model/plan/hook domains. This breaks domain ownership and makes the config package a grab-bag. Moving the interfaces clarifies ownership and aligns with layered domain grouping.

## What Changes
- Move `IToolManager` to `dare_framework3_4/tool/interfaces.py`.
- Move `IModelAdapterManager` to `dare_framework3_4/model/interfaces.py`.
- Move `IPlannerManager`, `IValidatorManager`, and `IRemediatorManager` to `dare_framework3_4/plan/interfaces.py`.
- Introduce `dare_framework3_4/hook/interfaces.py` and move `IHookManager` there.
- Define `IProtocolAdapterManager` at the package root in `dare_framework3_4/protocol_adapter_manager.py`.
- Remove `dare_framework3_4/config/interfaces.py` and the config facade re-exports (no compatibility aliases).
- Update `dare_framework3_4` imports to the new module paths.
- Resolve circular imports in `dare_framework/execution` by switching impl modules to import from their local protocol/model modules instead of the kernel/types facades.

## Impact
- Affected specs: `interface-layer`.
- Affected code: `dare_framework3_4/config`, `dare_framework3_4/tool`, `dare_framework3_4/model`, `dare_framework3_4/plan`, `dare_framework3_4/hook`, `dare_framework3_4/protocol_adapter_manager.py`, `dare_framework/execution/impl`.
