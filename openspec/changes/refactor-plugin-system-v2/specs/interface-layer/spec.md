## REMOVED Requirements

### Requirement: v1 runtime orchestration and gates
The system no longer treats v1-era contracts as primary runtime surfaces (e.g., `IContextAssembler`, `IToolRuntime`, `ICheckpoint`, `IPolicyEngine`).

#### Scenario: Kernel does not depend on v1 contracts
- **GIVEN** the v2 Kernel runtime
- **WHEN** importing Kernel modules
- **THEN** they do not import or depend on legacy v1 `dare_framework.core.*` runtime contracts

## MODIFIED Requirements

### Requirement: Shared types are v2-aligned
The system SHALL locate shared canonical types (evidence, risk levels, tool results/definitions, model message types) in v2-aligned modules and SHALL use them across Kernel/components/examples.

#### Scenario: Tool loop returns canonical ToolResult
- **GIVEN** a tool invocation through the v2 Tool Loop
- **WHEN** it completes
- **THEN** the result is represented using the canonical v2 `ToolResult` type (not a legacy v1-only type)
