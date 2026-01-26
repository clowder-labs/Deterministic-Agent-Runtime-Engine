## MODIFIED Requirements

### Requirement: Effective Config Object
The ConfigProvider SHALL return a single effective `Config` object that represents the resolved configuration. The effective `Config` MUST be immutable and safe to share across runtime components.

#### Scenario: Provider returns Config directly
- **WHEN** the configuration provider returns the effective configuration
- **THEN** it returns an immutable `Config` object directly (not wrapped in a `ConfigSnapshot`)

