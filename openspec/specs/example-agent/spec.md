# example-agent Specification

## Purpose
TBD - created by archiving the prior plugin-system change. Update Purpose after archive.
## Requirements
### Requirement: Verification examples track canonical contracts
The coding-agent verification examples SHALL remain present and SHALL be updated to use the canonical contracts and plugin system.

#### Scenario: Real-model coding agent example imports builder/contracts
- **GIVEN** `examples/coding-agent/real_model_agent.py`
- **WHEN** it is executed in a configured environment
- **THEN** it composes the agent using builder + plugin loading (and does not depend on removed v1 runtime interfaces)

### Requirement: Framework-Backed Coding Agent Example
The example agent SHALL be built using the developer API and SHALL register tools/providers in a way that exercises the Kernel `IToolGateway` boundary.

#### Scenario: Example agent instantiation
- **WHEN** a developer instantiates the example agent
- **THEN** it composes Kernel defaults, a deterministic planner/model adapter, and a minimal tool set

### Requirement: Deterministic Mock Mode
The example agent SHALL support a deterministic mode that uses a MockModelAdapter and/or DeterministicPlanGenerator to avoid external LLM calls.

#### Scenario: Mocked run
- **WHEN** the agent runs in deterministic mode
- **THEN** it completes the workflow without network access and returns fixed outputs

### Requirement: Optional Real Model Adapter
The example agent SHALL allow configuration of a real IModelAdapter, and this path SHALL remain optional and non-default.

#### Scenario: Real model configured
- **WHEN** a user configures a real model adapter
- **THEN** the agent delegates plan/execute generation to that adapter

### Requirement: Example Flow Validation
The repository SHALL include an integration test (or equivalent validation) that runs the example end-to-end in deterministic/mock mode and asserts a successful RunResult, including event log evidence.

#### Scenario: Example flow test
- **WHEN** the example flow test is executed
- **THEN** it completes without network access and asserts success + key audit events
