## 1. Manager refactor
- [x] 1.1 Add BaseComponentManager with shared entry point discovery, ordering, init, and register logic.
- [x] 1.2 Add per-interface managers (Validator/Memory/ModelAdapter/Tool/Skill/MCPClient/Hook/ConfigProvider/PromptStore) that inherit BaseComponentManager.
- [x] 1.3 Remove ComponentManager and ComponentDiscoveryConfig wiring from builder/runtime.

## 2. Wiring updates
- [x] 2.1 Update AgentBuilder to use per-interface managers and accept IConfigProvider input.
- [x] 2.2 Ensure managers return ordered lists of typed components (e.g., list[IValidator]).

## 3. Docs + alignment
- [x] 3.1 Update `doc/design/Architecture_Final_Review_v1.3.md` to describe per-interface managers and BaseComponentManager.
- [x] 3.2 Update `doc/design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md` to reflect manager split and always-on entry points.

## 4. Tests
- [x] 4.1 Update/replace ComponentManager tests for BaseComponentManager and typed managers.
- [x] 4.2 Verify builder wiring with manager outputs in unit tests.
