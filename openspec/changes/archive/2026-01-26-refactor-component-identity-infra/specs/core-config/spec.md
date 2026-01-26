## MODIFIED Requirements

### Requirement: ComponentType in contracts
The `ComponentType` enum SHALL be located in `dare_framework/infra/component.py` as a cross-domain shared type.

#### Scenario: All layers import ComponentType from infra
- **WHEN** any layer (config, builder, kernel defaults, components) needs `ComponentType`
- **THEN** it MUST import from `dare_framework.infra.component`.
