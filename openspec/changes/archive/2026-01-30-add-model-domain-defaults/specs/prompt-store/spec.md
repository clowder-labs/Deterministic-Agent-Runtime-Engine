## ADDED Requirements
### Requirement: Default prompt store factory
The model domain SHALL provide a public factory function for constructing the default prompt store, and cross-domain callers MUST use that factory instead of importing `_internal` prompt store implementations directly.

#### Scenario: Builder constructs default prompt store
- **GIVEN** a builder that needs the default prompt store
- **WHEN** it constructs the store
- **THEN** it calls the model domain prompt store factory and does not import `_internal` implementations
