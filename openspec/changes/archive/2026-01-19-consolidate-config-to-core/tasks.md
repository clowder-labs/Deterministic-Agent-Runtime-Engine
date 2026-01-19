## 1. Preparation
- [x] 1.1 Audit all imports of `dare_framework.config` and `dare_framework.components.config_providers` across the codebase.
- [x] 1.2 Identify tests that depend on current config module structure.

## 2. Move ComponentType to Contracts
- [x] 2.1 Create `dare_framework/contracts/component_type.py` with `ComponentType` enum.
- [x] 2.2 Update `dare_framework/contracts/__init__.py` to export `ComponentType`.
- [x] 2.3 Update all imports from `components.plugin_system.component_type` to `contracts.component_type`.
- [x] 2.4 Delete `dare_framework/components/plugin_system/component_type.py`.

## 3. Create New Core Config Module
- [x] 3.1 Create `dare_framework/core/config/models.py` with `Config`, `LLMConfig`, `ComponentConfig` data models.
- [x] 3.2 Create `dare_framework/core/config/manager.py` with `ConfigManager` class implementing layered merge logic.
- [x] 3.3 Create `dare_framework/core/config/__init__.py` facade exporting public API.

## 4. Migration
- [x] 4.1 Update `dare_framework/builder.py` to use `core.config.ConfigManager`.
- [x] 4.2 Update `dare_framework/core/tool/run_context_state.py` to import from `core.config`.
- [x] 4.3 Update `dare_framework/components/plugin_system/entrypoint_managers.py` imports.
- [x] 4.4 Update `dare_framework/components/model_adapters/openai.py` imports.
- [x] 4.5 Update all test files to use new import paths.

## 5. Cleanup
- [x] 5.1 Remove `dare_framework/config/` directory.
- [x] 5.2 Remove `dare_framework/components/config_providers/` directory.
- [x] 5.3 Remove `IConfigProviderManager` from `dare_framework/components/plugin_system/managers.py`.
- [x] 5.4 Update `PluginManagers` dataclass to remove `config_providers` field.

## 6. Verification
- [x] 6.1 Run full test suite to ensure no regressions.
- [x] 6.2 Verify package facade pattern compliance for `core/config/__init__.py`.
- [x] 6.3 Verify no circular imports exist.
