## MODIFIED Requirements

### Requirement: Core Interface Coverage
The interface layer SHALL define Kernel and Component contracts, including a shared component identity contract (`IComponent`) and the shared `ComponentType` enum.

#### Scenario: Developer imports shared component identity
- **WHEN** a developer implements a pluggable component
- **THEN** they can implement `IComponent` and reference `ComponentType` from the canonical infra module
