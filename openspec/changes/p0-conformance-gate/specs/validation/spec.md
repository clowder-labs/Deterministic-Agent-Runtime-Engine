## MODIFIED Requirements

### Requirement: Composite validator
The system SHALL provide a CompositeValidator that chains multiple validators in ascending order and aggregates validation errors.

For P0 conformance, composite validation MUST support invariant-focused validators whose failures are propagated with stable failure categories.

#### Scenario: Aggregated validation errors
- **WHEN** any validator in the chain fails
- **THEN** the CompositeValidator MUST return failure and include all collected errors

#### Scenario: Conformance validator failure is categorized
- **WHEN** a P0 invariant validator fails
- **THEN** returned errors include a stable category label suitable for CI conformance reporting

