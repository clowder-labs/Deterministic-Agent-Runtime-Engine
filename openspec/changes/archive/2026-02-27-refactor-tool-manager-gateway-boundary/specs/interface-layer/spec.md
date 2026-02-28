## MODIFIED Requirements
### Requirement: Default ToolGateway Aggregates Capability Providers
The canonical `dare_framework` package SHALL provide a default `IToolGateway` implementation (`ToolGateway`) that is backed by `IToolManager` capability state. The gateway MUST enforce envelope allowlists during invocation and MUST resolve tools through the manager registry.

#### Scenario: List capabilities from manager-backed gateway
- **GIVEN** two registered tool providers in the manager
- **WHEN** `ToolGateway.list_capabilities()` is called
- **THEN** it returns the combined capability descriptors without duplicate ids

#### Scenario: Reject disallowed capability invoke
- **GIVEN** an envelope with `allowed_capability_ids` that does not include a requested capability
- **WHEN** `ToolGateway.invoke()` is called
- **THEN** the gateway rejects the request

### Requirement: Tool manager contract
The tool domain SHALL define an `IToolManager` contract in `dare_framework/tool/kernel.py` for trusted tool registration, provider aggregation, and capability metadata export. `IToolManager` SHALL NOT be the invocation boundary and SHALL NOT require `invoke(...)`.

At minimum it MUST include:
- `register_tool(...)`, `unregister_tool(...)`, `update_tool(...)`
- `register_provider(...)`, `unregister_provider(...)`
- `list_capabilities(...)`, `refresh(...)`
- `list_tool_defs(...)`, `get_capability(...)`
- `health_check(...)`

#### Scenario: Tool manager is not used as gateway
- **GIVEN** the default `ToolManager` implementation
- **WHEN** a runtime invocation is needed
- **THEN** invocation flows through `IToolGateway.invoke(...)`
- **AND** the manager is used only for capability lookup and lifecycle state
