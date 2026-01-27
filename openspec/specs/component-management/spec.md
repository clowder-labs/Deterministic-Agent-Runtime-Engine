# component-management Specification

## Purpose
TBD - created by archiving change add-component-manager-entrypoints. Update Purpose after archive.
## Requirements
### Requirement: Component lifecycle interface
The system SHALL define `IComponent` as the canonical identity contract for pluggable components.

`IComponent` MUST expose:
- `component_type: ComponentType`
- `name: str`

#### Scenario: Config filters components by identity
- **GIVEN** a manager returns a list of components
- **WHEN** config filtering is applied
- **THEN** the system can read `component_type` and `name` from each component to evaluate enablement

### Requirement: Component discovery via entry points
The system SHALL support entry point discovery for pluggable components via per-interface managers (Validator/Memory/ModelAdapter/Tool/Skill/MCPClient/Hook/ConfigProvider/PromptStore). Each manager SHALL inherit BaseComponentManager and return an ordered list of its managed components when provided an IConfigProvider.

#### Scenario: Validator manager discovery
- **WHEN** ValidatorManager loads entry points
- **THEN** it MUST return a list of IValidator ordered by ascending IComponent.order

#### Scenario: Memory manager discovery
- **WHEN** MemoryManager loads entry points with an IConfigProvider
- **THEN** it MUST initialize and register IMemory components and return the ordered list

### Requirement: Ordered registration
The system SHALL order discovered components by ascending `order` value before initialization and registration.

#### Scenario: Order determines precedence
- **WHEN** two components are discovered with `order` values of 10 and 50
- **THEN** the component with order 10 MUST initialize and register first

### Requirement: Lifecycle ownership boundary
The system SHALL only manage lifecycle (init/close) for components it creates and MUST NOT close externally injected component instances.

Additionally, configuration-driven enable/disable filtering MUST apply only to components produced by managers and MUST NOT remove or silently drop externally injected components.

#### Scenario: Caller-injected component lifecycle
- **WHEN** a caller injects a component instance directly into an agent builder
- **THEN** the framework MUST NOT call `close()` automatically for that instance

#### Scenario: Config disabled does not remove injected component
- **GIVEN** a caller injects a tool instance into the builder
- **AND** config marks that tool name as disabled for the tool component type
- **WHEN** the builder assembles components using managers + config
- **THEN** the injected tool MUST remain present and only manager-loaded tools are subject to config filtering

### Requirement: Composite tool assembly
ToolManager SHALL support registering composite tools defined by configuration recipes (name, optional description, ordered steps referencing existing tools).

#### Scenario: Composite tool from config
- **WHEN** config defines `composite_tools` with a recipe containing `steps` referencing known tools
- **THEN** ToolManager assembles and registers a CompositeTool that executes the referenced tools sequentially

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

