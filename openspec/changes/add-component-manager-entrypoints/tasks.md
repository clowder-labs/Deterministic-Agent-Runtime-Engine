## 1. Component lifecycle + discovery
- [x] 1.1 Add `IComponent` base interface with `order`, `init`, `register`, and optional `close` hooks.
- [x] 1.2 Update Layer 2 pluggable interfaces to inherit `IComponent` (IModelAdapter, IMemory, IValidator, ITool, ISkill, IMCPClient, IHook, IConfigProvider, IPromptStore).
- [x] 1.3 Add `IConfigProvider` and `IPromptStore` interfaces to core.
- [x] 1.4 Implement ComponentManager in Layer 3 with entry point discovery, ordering, and registration.
- [x] 1.5 Add entry point group conventions and configuration to enable/disable discovery.

## 2. Validation composition
- [x] 2.1 Implement CompositeValidator (ordered chain, aggregated errors).
- [x] 2.2 Ensure validator implementations live in Layer 2 components and are discoverable/registrable by ComponentManager.
- [x] 2.3 Update runtime/builder wiring to use CompositeValidator by default.

## 3. Docs + alignment
- [x] 3.1 Update `doc/design/Architecture_Final_Review_v1.3.md` to include ComponentManager and entry point discovery.
- [x] 3.2 Update `doc/design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md` for component lifecycle and config/prompt interfaces.

## 4. Tests
- [x] 4.1 Add unit tests for ComponentManager ordering, discovery filters, and lifecycle ownership.
- [x] 4.2 Add unit tests for CompositeValidator ordering + error aggregation.
