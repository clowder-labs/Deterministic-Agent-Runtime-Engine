## MODIFIED Requirements
### Requirement: Tool manager aggregates providers and exports tool defs
ToolManager SHALL aggregate `IToolProvider` instances and refresh their capabilities into the registry. It MUST provide prompt tool definitions derived from the registry and MUST NOT execute tool side-effects; invocation is owned by `IToolGateway` (implemented by ToolManager).

Provider-derived metadata coercion MUST be robust: malformed provider metadata values MUST NOT crash registry aggregation.

#### Scenario: Provider capabilities are visible in the registry
- **GIVEN** a provider is registered with the ToolManager
- **WHEN** `refresh()` is called
- **THEN** its capabilities are available via `list_capabilities()`

#### Scenario: Invalid provider timeout metadata falls back safely
- **GIVEN** a provider exposes a tool with non-numeric `timeout_seconds`
- **WHEN** ToolManager aggregates provider capabilities
- **THEN** capability registration does not fail
- **AND** the effective timeout metadata falls back to the default value

#### Scenario: Tool manager does not invoke tools
- **GIVEN** a tool capability is registered
- **WHEN** an invocation is needed
- **THEN** the system routes the call through `IToolGateway.invoke(...)` (ToolManager implements the gateway)
