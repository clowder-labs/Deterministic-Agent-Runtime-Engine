## ADDED Requirements
### Requirement: Component lifecycle interface
The system SHALL define `IComponent` with an `order` attribute, an async `init()` hook, a `register()` hook, and an async `close()` hook. Layer 2 pluggable interfaces MUST implement or extend `IComponent` (IModelAdapter, IMemory, IValidator, ITool, ISkill, IMCPClient, IHook, IConfigProvider, IPromptStore).

#### Scenario: Managed component lifecycle
- **WHEN** ComponentManager instantiates a component discovered via entry points
- **THEN** it MUST call `init()` before `register()` and MUST call `close()` on shutdown

#### Scenario: Pluggable interface conformance
- **WHEN** a Layer 2 implementation provides IModelAdapter or IMemory functionality
- **THEN** it MUST implement `IComponent` to participate in ordering and registration

### Requirement: Component discovery via entry points
The system SHALL support entry point discovery for pluggable components, grouped by interface type (validators, memory, model adapters, tools, skills, MCP clients, hooks, config providers, prompt stores).

#### Scenario: Discovery populates registries
- **WHEN** entry point discovery is enabled
- **THEN** discovered components MUST be registered into the appropriate registries

### Requirement: Ordered registration
The system SHALL order discovered components by ascending `order` value before initialization and registration.

#### Scenario: Order determines precedence
- **WHEN** two components are discovered with `order` values of 10 and 50
- **THEN** the component with order 10 MUST initialize and register first

### Requirement: Lifecycle ownership boundary
The system SHALL only manage lifecycle (init/close) for components it creates and MUST NOT close externally injected component instances.

#### Scenario: Caller-injected component
- **WHEN** a caller injects a component instance directly into AgentBuilder
- **THEN** ComponentManager MUST register it but MUST NOT call `close()` automatically
