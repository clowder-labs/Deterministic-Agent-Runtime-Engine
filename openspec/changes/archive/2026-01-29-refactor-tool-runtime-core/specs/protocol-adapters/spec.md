## MODIFIED Requirements

### Requirement: Protocol adapter surface is deferred
The framework SHALL NOT expose protocol adapter interfaces until a dedicated integration is specified.

#### Scenario: Protocol adapters are not available
- **WHEN** a contributor looks for protocol adapter contracts
- **THEN** only local tool/provider surfaces are available
