## 1. Specification
- [x] 1.1 Define `IToolManager` contract and behaviors in interface-layer spec
- [x] 1.2 Define Tool Manager registry and provider aggregation requirements in component-management spec

## 2. Implementation
- [x] 2.1 Add `IToolManager` interface in `dare_framework/tool/interfaces.py`
- [x] 2.2 Implement ToolManager registry + provider aggregation in `dare_framework/tool/_internal/managers/`
- [x] 2.3 Wire ToolManager into tool facade exports and internal aggregates
- [x] 2.4 Update builder/context integration to use ToolManager for prompt tool defs

## 3. Tests
- [x] 3.1 Registry tests: register/update/unregister, enable/disable, metadata trust
- [x] 3.2 Provider aggregation tests: multi-provider, refresh, duplicate id handling
- [x] 3.3 Tool defs export tests: tool defs match capability registry
