## MODIFIED Requirements

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

