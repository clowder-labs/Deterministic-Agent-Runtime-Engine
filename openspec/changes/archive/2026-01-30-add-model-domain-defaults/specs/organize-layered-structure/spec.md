## ADDED Requirements
### Requirement: Internal implementation boundary
Domain implementations in `_internal/` SHALL NOT be imported directly by other domains; instead, the owning domain MUST expose public factory functions or facades for default implementations.

#### Scenario: External domain uses factory
- **GIVEN** a builder in another domain needs a default implementation
- **WHEN** it accesses that implementation
- **THEN** it uses the owning domain's factory or facade rather than importing `_internal` modules
