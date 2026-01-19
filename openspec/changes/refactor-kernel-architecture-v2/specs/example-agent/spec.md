## MODIFIED Requirements
### Requirement: Framework-Backed Example Uses v2 Developer API
The example agent SHALL be built using the v2 developer API and SHALL register tools/providers in a way that exercises the Kernel `IToolGateway` boundary.

#### Scenario: Example agent instantiation
- **WHEN** a developer instantiates the example agent
- **THEN** it composes Kernel defaults, a deterministic planner/model adapter, and a minimal tool set

### Requirement: Deterministic Closed-Loop Validation (v2)
The repository SHALL include an integration test (or equivalent validation) that runs the example end-to-end in deterministic/mock mode and asserts a successful RunResult, including event log evidence.

#### Scenario: Example flow test
- **WHEN** the example flow test is executed
- **THEN** it completes without network access and asserts success + key audit events

