## 1. Interface relocation
- [x] 1.1 Add manager Protocols to the domain interface modules (`tool`, `model`, `plan`, `hook`).
- [x] 1.2 Add `dare_framework3_4/protocol_adapter_manager.py` with `IProtocolAdapterManager`.
- [x] 1.3 Remove `dare_framework3_4/config/interfaces.py`.

## 2. Import and facade updates
- [x] 2.1 Update `dare_framework3_4/config/__init__.py` to export only config types and `IConfigProvider`.
- [x] 2.2 Update `dare_framework3_4` imports to the new manager interface paths.
- [x] 2.3 Resolve unit-test circular imports in `dare_framework/execution` (move impl modules to direct protocol/model imports).

## 3. Validation
- [x] 3.1 Run `python -m pytest tests/unit` (or the smallest relevant subset available) and note results.
      Result: 24 passed.
