## 1. Implementation
- [x] 1.1 Remove `IToolGateway` implementation and `invoke(...)` from `ToolManager`.
- [x] 1.2 Update `ToolGateway` to depend on `IToolManager` and keep invocation logic there.
- [x] 1.3 Update builder tool wiring to always compose a dedicated `ToolGateway` with the selected manager.
- [x] 1.4 Update/extend unit tests for manager-vs-gateway separation and invocation behavior.

## 2. Verification
- [x] 2.1 Run targeted unit tests for tool manager/gateway and builder wiring.
- [x] 2.2 Run adjacent unit tests covering registry validation/context tool listing paths.
