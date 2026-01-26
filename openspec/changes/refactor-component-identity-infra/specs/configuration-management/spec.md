## ADDED Requirements

### Requirement: Config enablement helpers accept components
The `Config` model SHALL expose helper APIs that accept concrete component instances for enablement evaluation and filtering.

#### Scenario: Filter manager-loaded components by config
- **GIVEN** a list of components loaded by a manager
- **WHEN** config filters the list
- **THEN** only enabled components remain, using each component's type and name for lookup

## MODIFIED Requirements

### Requirement: Component Identity for Configuration
Each entry point component implementation SHALL expose a component type and name for configuration lookup.

The canonical identity surface SHALL be `infra.IComponent.component_type` and `infra.IComponent.name`, and SHALL use the shared `ComponentType` enum for types.

#### Scenario: Component exposes type for config lookup
- **WHEN** a component is discovered via entry points or provided by a manager
- **THEN** config filtering can read its `component_type` and `name` for enable/disable evaluation
