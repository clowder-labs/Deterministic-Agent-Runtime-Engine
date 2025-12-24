## ADDED Requirements
### Requirement: Composite validator
The system SHALL provide a CompositeValidator that chains multiple validators in ascending order and aggregates validation errors.

#### Scenario: Aggregated validation errors
- **WHEN** any validator in the chain fails
- **THEN** the CompositeValidator MUST return failure and include all collected errors
