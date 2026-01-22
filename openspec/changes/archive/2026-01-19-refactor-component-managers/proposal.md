# Change: Refactor component managers by interface type

## Why
The current single ComponentManager centralizes discovery and registration with hardcoded branching. We want a clearer, layered design: each IComponent type is managed by its own manager, inheriting shared loader/init/register logic from a base manager. This keeps the system extensible and avoids a monolithic if/else dispatcher.

## What Changes
- Replace the global ComponentManager with per-interface managers (ValidatorManager, MemoryManager, ModelAdapterManager, ToolManager, SkillManager, MCPClientManager, HookManager, ConfigProviderManager, PromptStoreManager).
- Introduce a BaseComponentManager that encapsulates shared load/init/register logic and entry point discovery.
- Managers always use entry points for discovery (no enable/disable config); each manager exposes a method that accepts IConfigProvider and returns an ordered list of components it manages.
- Update builder/runtime wiring to use the new managers and remove the old ComponentManager/ComponentDiscoveryConfig.
- Update architecture/interface docs to reflect the manager split and ownership model.

## Impact
- Affected specs: component-management
- Affected code: component management, builder wiring, registries, tests
- Affected docs: `doc/design/archive/Architecture_Final_Review_v1.3.md`, `doc/design/archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md`
