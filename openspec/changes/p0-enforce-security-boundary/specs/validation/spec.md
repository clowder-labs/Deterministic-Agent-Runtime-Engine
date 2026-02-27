## MODIFIED Requirements

### Requirement: Composite validator
The system SHALL provide a CompositeValidator that chains multiple validators in ascending order and aggregates validation errors.

Composite validation for security-sensitive plans MUST include trusted metadata checks and MUST fail when required trusted fields cannot be derived from registry-backed sources.

#### Scenario: Aggregated validation errors
- **WHEN** any validator in the chain fails
- **THEN** the CompositeValidator MUST return failure and include all collected errors

#### Scenario: Missing trusted security metadata fails validation
- **WHEN** a proposed step references a capability but trusted risk metadata cannot be derived
- **THEN** validation returns failure
- **AND** the error set includes a security metadata derivation error

