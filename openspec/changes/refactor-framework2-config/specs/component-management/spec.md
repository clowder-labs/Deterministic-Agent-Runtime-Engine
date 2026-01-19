## MODIFIED Requirements
### Requirement: Component lifecycle interface
The system SHALL define `IComponent` with an `order` attribute, an async `init()` hook, a `register()` hook, and an async `close()` hook. Layer 2 pluggable interfaces MUST implement or extend `IComponent` (IModelAdapter, IMemory, IValidator, ITool, ISkill, IMCPClient, IHook, IPromptStore). Configuration management is handled outside the component lifecycle.

#### Scenario: Managed component lifecycle
- **WHEN** ComponentManager instantiates a component discovered via entry points
- **THEN** it MUST call `init()` before `register()` and MUST call `close()` on shutdown

#### Scenario: Pluggable interface conformance
- **WHEN** a Layer 2 implementation provides IModelAdapter or IMemory functionality
- **THEN** it MUST implement `IComponent` to participate in ordering and registration

### Requirement: Component discovery via entry points
The system SHALL support entry point discovery for pluggable components via per-interface managers (Validator/Memory/ModelAdapter/Tool/Skill/MCPClient/Hook/PromptStore). Each manager SHALL inherit BaseComponentManager and return an ordered list of its managed components when provided configuration.

#### Scenario: Validator manager discovery
- **WHEN** ValidatorManager loads entry points
- **THEN** it MUST return a list of IValidator ordered by ascending IComponent.order

#### Scenario: Memory manager discovery
- **WHEN** MemoryManager loads entry points with configuration
- **THEN** it MUST initialize and register IMemory components and return the ordered list
