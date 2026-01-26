## MODIFIED Requirements

### Requirement: Component lifecycle interface
The system SHALL define `IComponent` as the canonical identity contract for pluggable components.

`IComponent` MUST expose:
- `component_type: ComponentType`
- `name: str`

#### Scenario: Config filters components by identity
- **GIVEN** a manager returns a list of components
- **WHEN** config filtering is applied
- **THEN** the system can read `component_type` and `name` from each component to evaluate enablement
