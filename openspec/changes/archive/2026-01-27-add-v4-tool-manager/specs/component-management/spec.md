## ADDED Requirements
### Requirement: Tool manager maintains trusted capability registry
ToolManager SHALL maintain the trusted capability registry for tools. It MUST:
- Register, update, and unregister tool capabilities
- Generate stable capability identifiers (namespace + name, optional version)
- Track enable/disable state per capability
- Persist trusted metadata (`risk_level`, `requires_approval`, `timeout_seconds`, `is_work_unit`, `capability_kind`)

#### Scenario: Disabled tool is excluded from tool defs
- **GIVEN** a tool is registered and then disabled
- **WHEN** `list_tool_defs()` is requested
- **THEN** the disabled capability is not included in prompt tools

#### Scenario: Registry metadata overrides untrusted input
- **GIVEN** a model proposes tool metadata that conflicts with registry metadata
- **WHEN** policy evaluation occurs
- **THEN** the system uses ToolManager registry metadata as the source of truth

### Requirement: Tool manager aggregates providers and exports tool defs
ToolManager SHALL aggregate `ICapabilityProvider` instances and refresh their capabilities into the registry. It MUST provide prompt tool definitions derived from the registry and MUST NOT execute tool side‑effects; invocation is owned by `IToolGateway`.

#### Scenario: Provider capabilities are visible in the registry
- **GIVEN** a provider is registered with the ToolManager
- **WHEN** `refresh()` is called
- **THEN** its capabilities are available via `list_capabilities()`

#### Scenario: Tool manager does not invoke tools
- **GIVEN** a tool capability is registered
- **WHEN** an invocation is needed
- **THEN** the system routes the call through `IToolGateway.invoke(...)` rather than the ToolManager
