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
- Use `tool.name` as the `capability_id` and reject duplicate names
- Track enable/disable state per capability
- Persist trusted metadata (`risk_level`, `requires_approval`, `timeout_seconds`, `is_work_unit`, `capability_kind`)
- Serve as the source of truth for runtime tool activation

Capability `input_schema` and `output_schema` MUST be derived from each tool's `execute` contract (signature, type annotations, and doc comments for descriptions), rather than manually duplicated schema literals.

#### Scenario: Registry schema follows execute signature
- **GIVEN** a registered tool with explicit execute keyword parameters
- **WHEN** ToolManager builds a capability descriptor
- **THEN** descriptor schemas match execute parameter and return annotations
- **AND** schema field descriptions reflect execute doc comments when provided

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

### Requirement: Skill store builder composes loaders deterministically
The skill domain SHALL provide a `SkillStoreBuilder` that deterministically composes skill loaders and filtering rules before constructing an `ISkillStore`.

- `SkillStoreBuilder.config(config)` MUST derive filesystem skill loading roots from `Config.workspace_dir` and `Config.user_dir`.
- The builder MUST allow callers to append external skill loaders.
- The builder MUST support disabling skills by `skill_id` before final store exposure.
- The resulting `ISkillStore` MUST provide deterministic `list_skills()` and `get_skill(skill_id)` behavior after composition.

#### Scenario: Config-derived loader and external loader are combined
- **GIVEN** a `Config` with workspace and user directories
- **AND** an external loader is attached to `SkillStoreBuilder`
- **WHEN** `build()` is called
- **THEN** the resulting store contains skills from both config-derived filesystem loading and the external loader

#### Scenario: Disabled skill ids are filtered out
- **GIVEN** a composed skill store contains skill ids `a`, `b`, and `c`
- **AND** `disable_skill("b")` is configured
- **WHEN** `build()` is called
- **THEN** `list_skills()` excludes `b`
- **AND** `get_skill("b")` returns `None`

### Requirement: DareAgentBuilder exposes execution-mode wiring

`DareAgentBuilder` SHALL expose explicit builder APIs for execution strategy wiring so callers can deterministically select runtime behavior.

#### Scenario: Builder sets execution mode explicitly

- **GIVEN** a `DareAgentBuilder`
- **WHEN** caller configures `with_execution_mode("step_driven")`
- **THEN** built `DareAgent` runs with `execution_mode="step_driven"`

#### Scenario: Builder injects custom step executor

- **GIVEN** a custom `IStepExecutor` implementation
- **WHEN** caller configures `with_step_executor(custom_executor)`
- **THEN** built `DareAgent` uses that executor in step-driven mode

#### Scenario: Builder default remains model-driven

- **GIVEN** a `DareAgentBuilder` with no execution-mode customization
- **WHEN** the agent is built
- **THEN** `execution_mode` remains `model_driven`
- **AND** existing model-driven runtime behavior is unchanged

