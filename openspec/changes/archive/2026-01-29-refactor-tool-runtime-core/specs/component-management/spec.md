## MODIFIED Requirements

### Requirement: Tool manager maintains trusted capability registry
ToolManager SHALL maintain the trusted capability registry for tools. It MUST:
- Register, update, and unregister tool capabilities
- Generate unique capability identifiers (UUID) to avoid tool name collisions
- Track enable/disable state per capability
- Persist trusted metadata (`risk_level`, `requires_approval`, `timeout_seconds`, `is_work_unit`, `capability_kind`)
- Preserve the original tool name in registry metadata for display/audit
- Serve as the source of truth for runtime tool activation and invocation

#### Scenario: Disabled tool is excluded from tool defs
- **GIVEN** a tool is registered and then disabled
- **WHEN** `list_tool_defs()` is requested
- **THEN** the disabled capability is not included in prompt tools

#### Scenario: Registry controls invokable tools
- **GIVEN** a tool is not registered (or is disabled)
- **WHEN** the runtime attempts to invoke it via the ToolManager gateway boundary
- **THEN** the invocation is rejected

### Requirement: Tool manager aggregates providers and exports tool defs
ToolManager SHALL aggregate `IToolProvider` instances and refresh their capabilities into the registry. It MUST provide prompt tool definitions derived from the registry and MUST NOT execute tool side-effects; invocation is owned by `IToolGateway` (implemented by ToolManager).

#### Scenario: Provider capabilities are visible in the registry
- **GIVEN** a provider is registered with the ToolManager
- **WHEN** `refresh()` is called
- **THEN** its capabilities are available via `list_capabilities()`

#### Scenario: Tool manager does not invoke tools
- **GIVEN** a tool capability is registered
- **WHEN** an invocation is needed
- **THEN** the system routes the call through `IToolGateway.invoke(...)` (ToolManager implements the gateway)
