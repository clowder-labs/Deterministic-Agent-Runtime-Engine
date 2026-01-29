## MODIFIED Requirements

### Requirement: Default ToolGateway Aggregates Capability Providers
The canonical `dare_framework` package SHALL provide a default `IToolGateway` implementation backed by `IToolManager` that aggregates registered `IToolProvider` instances and enforces envelope allowlists during invocation.

#### Scenario: List capabilities from multiple providers
- **GIVEN** two registered tool providers
- **WHEN** `list_capabilities()` is called
- **THEN** it returns the combined capability descriptors without duplicate ids

#### Scenario: Reject disallowed capability invoke
- **GIVEN** an envelope with `allowed_capability_ids` that does not include a requested capability
- **WHEN** `invoke()` is called
- **THEN** the gateway rejects the request

### Requirement: Tool manager contract
The tool domain SHALL define an `IToolManager` contract in `dare_framework/tool/kernel.py` that extends `IToolGateway`. The contract SHALL support trusted tool registration, provider aggregation, and prompt tool definition export without executing tools. At minimum it MUST include:
- `register_tool(...)`, `unregister_tool(...)`, `update_tool(...)`
- `register_provider(...)`, `unregister_provider(...)`
- `list_capabilities(...)`, `refresh(...)`
- `list_tool_defs(...)`, `get_capability(...)`
- `health_check(...)`

#### Scenario: Register tool returns a capability descriptor
- **GIVEN** a valid `ITool` implementation
- **WHEN** `register_tool(...)` is called
- **THEN** the manager returns a `CapabilityDescriptor` with a stable `capability_id` and trusted metadata

#### Scenario: Tool definitions are derived from registry
- **GIVEN** a tool has been registered into the manager
- **WHEN** `list_tool_defs()` is called
- **THEN** the result is derived from the manager registry and not from model output

## ADDED Requirements

### Requirement: Tool providers return ITool lists
`IToolProvider` SHALL return tool instances rather than tool definitions. The provider acts only as a tool source for registration into ToolManager.

#### Scenario: Provider supplies tools for registration
- **GIVEN** an `IToolProvider`
- **WHEN** `list_tools()` is called
- **THEN** it returns an ordered `list[ITool]` suitable for registration into ToolManager

### Requirement: Capability id is the tool call identity
The system SHALL use a UUID-based `capability_id` as the canonical identity for tools. The LLM-facing tool definition MUST use `function.name == capability_id`, and ToolManager/ToolGateway MUST route invocations by this same identifier.

#### Scenario: Tool naming is consistent across LLM and routing
- **GIVEN** a tool registered into ToolManager
- **WHEN** the tool is exposed to the model
- **THEN** the tool definition name equals the tool’s `capability_id` and tool calls route by that value
