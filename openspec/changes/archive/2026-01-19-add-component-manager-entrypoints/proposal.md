# Change: Add component manager + entry point discovery

## Why
Layer 2 has multiple pluggable implementations (IMemory, IModelAdapter, IValidator, etc.), but there is no unified lifecycle/registration protocol or discovery path. This makes extension inconsistent and complicates layered ownership. Entry points give Python-native discovery without coupling core to concrete implementations.

## What Changes
- Introduce a base `IComponent` interface with `order`, `init`, and `register` to unify lifecycle/registration for Layer 2 pluggables (IModelAdapter, IMemory, IValidator, ITool, ISkill, IMCPClient, IHook, IConfigProvider, IPromptStore).
- Add a Layer 3 ComponentManager that discovers pluggable implementations via entry points, orders them, initializes them, and registers them to the appropriate registries.
- Add composite validator support (chained validators with ordered execution and aggregated errors).
- Add interfaces for configuration (`IConfigProvider`) and prompt management (`IPromptStore`).
- Document the layer boundaries and discovery rules in architecture/interface docs.

## Impact
- Affected specs: component-management, validation, configuration, prompt-store
- Affected code: core interfaces, builder/manager composition, default components, plugin discovery, tests
- Affected docs: `doc/design/archive/Architecture_Final_Review_v1.3.md`, `doc/design/archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md`
