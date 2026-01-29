## 1. Implementation
- [x] Update tool interfaces: redefine `IToolProvider` to return `list[ITool]` and remove `ICapabilityProvider` from the runtime path
- [x] Promote ToolManager to implement `IToolGateway` and own the runtime tool registry
- [x] Centralize tool schema derivation (shared factory or ToolManager method)
- [x] Update builder/context to register tools into ToolManager and list tools via ToolManager
- [x] Update protocol adapters/MCP integration to register `ITool` instances into ToolManager
- [x] Remove or deprecate provider-based gateway wiring (NativeToolProvider/ProtocolAdapterProvider/GatewayToolProvider)

## 2. Documentation & Examples
- [x] Update tool examples to use ToolManager as tool gateway
- [x] Update docs mentioning capability providers or gateway aggregation

## 3. Tests
- [x] Add tests to assert tool list consistency with invokable registry
- [x] Add tests for tool group registration and config enable/disable
