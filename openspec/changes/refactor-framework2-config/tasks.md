## 1. Implementation
- [x] 1.1 Add `dare_framework2/config/manager.py` with `ConfigManager` + helper functions; move config dataclasses to `dare_framework2/config/models.py`; update `dare_framework2/config/__init__.py` to expose the new formal entry.
- [x] 1.2 Introduce `dare_framework2/contracts/component_type.py` and update `dare_framework2/builder/types.py` plus related imports to use it (re-export from builder).
- [x] 1.3 Remove config-provider plugin surface (`dare_framework2/config/interfaces.py`, `dare_framework2/config/impl/*`, `IConfigProviderManager` + no-op manager) and update builder exports.
- [x] 1.4 Wire `RunContextState.config` to `Config` and align builder/tool context usage.
- [x] 1.5 Add unit tests for `ConfigManager` (merge precedence, `get`/`get_namespace`, reload returns new `Config`, `config_hash` stability).
- [x] 1.6 Update docs/examples referencing old config providers or config import paths.

## 2. Validation
- [x] 2.1 Run `pytest -k config_manager` (or relevant subset).
