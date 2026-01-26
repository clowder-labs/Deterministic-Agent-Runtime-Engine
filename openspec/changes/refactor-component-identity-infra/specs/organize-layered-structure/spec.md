## MODIFIED Requirements

### Requirement: Layered Package Organization
The framework SHALL include an `infra` package for cross-domain shared contracts (e.g., `ComponentType`, `IComponent`) that are used by multiple domains.

#### Scenario: Contributor locates shared identity types
- **WHEN** a contributor needs `ComponentType` or `IComponent`
- **THEN** they find them under `dare_framework/infra/`
