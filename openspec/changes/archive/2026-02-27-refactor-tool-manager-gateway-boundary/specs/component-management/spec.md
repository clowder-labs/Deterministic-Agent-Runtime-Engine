## MODIFIED Requirements
### Requirement: Tool manager aggregates providers and exports tool defs
ToolManager SHALL aggregate `IToolProvider` instances and refresh their capabilities into the registry. It MUST provide prompt tool definitions derived from the registry and MUST NOT execute tool side-effects; invocation is owned by `IToolGateway` (implemented by `ToolGateway`).

Provider-derived metadata coercion MUST be robust: malformed provider metadata values MUST NOT crash registry aggregation.

#### Scenario: Provider capabilities are visible in the registry
- **GIVEN** a provider is registered with the ToolManager
- **WHEN** `refresh()` is called
- **THEN** its capabilities are available via `list_capabilities()`

#### Scenario: Tool manager does not invoke tools
- **GIVEN** a tool capability is registered
- **WHEN** an invocation is needed
- **THEN** the system routes the call through `ToolGateway.invoke(...)`
- **AND** `ToolGateway` resolves the callable tool via the manager registry
