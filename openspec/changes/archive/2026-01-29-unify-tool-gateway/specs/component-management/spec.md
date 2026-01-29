## MODIFIED Requirements
### Requirement: Tool manager aggregates providers and exports tool defs
ToolManager SHALL aggregate `IToolProvider` instances and refresh their capabilities into the registry. It MUST provide prompt tool definitions derived from the registry and MUST NOT execute tool side‑effects; invocation is owned by `IToolGateway` (implemented by ToolManager).

#### Scenario: Provider capabilities are visible in the registry
- **GIVEN** a provider is registered with the ToolManager
- **WHEN** `refresh()` is called
- **THEN** its capabilities are available via `list_capabilities()`

#### Scenario: Tool manager does not invoke tools
- **GIVEN** a tool capability is registered
- **WHEN** an invocation is needed
- **THEN** the system routes the call through `IToolGateway.invoke(...)` (ToolManager implements the gateway)
