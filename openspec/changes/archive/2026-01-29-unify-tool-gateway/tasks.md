## 1. Spec updates
- [x] 1.1 Update interface-layer requirements for ToolManager/ToolGateway relationship.
- [x] 1.2 Update component-management requirements to reflect single gateway surface.

## 2. Code changes
- [x] 2.1 Make `IToolManager` inherit from `IToolGateway` in kernel.
- [x] 2.2 Remove builder `tool_manager` wiring and enforce manager-compatible gateway for tool injection.
- [x] 2.3 Update docs/examples/tests to align with single gateway surface.

## 3. Validation
- [x] 3.1 Run `openspec validate unify-tool-gateway --strict`.
