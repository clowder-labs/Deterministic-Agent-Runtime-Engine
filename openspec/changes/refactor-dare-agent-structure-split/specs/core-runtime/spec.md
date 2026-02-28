## ADDED Requirements

### Requirement: DareAgent orchestration implementation is modularized with behavior parity
The runtime SHALL implement session/milestone/execute/tool orchestration through explicit internal execution modules while preserving the externally observable behavior of `DareAgent`.

- `DareAgent` MUST remain the public orchestration entry point and API owner.
- Core loop internals MUST be decomposed into dedicated execution units with clear ownership boundaries.
- Refactoring MUST NOT change existing runtime semantics for budget checks, hook emission, security policy gates, approval flow, event logging, and structured failure returns.

#### Scenario: Refactored orchestration preserves execution semantics
- **WHEN** the runtime executes the existing milestone/execute/tool paths after modularization
- **THEN** it preserves prior success/failure semantics, including policy gating and error normalization behavior

#### Scenario: Core loop logic is unit-testable without full agent integration
- **WHEN** loop behaviors are verified in targeted unit tests for extracted execution units
- **THEN** key control-flow branches (success, denial, approval-required, retry, failure) are validated without requiring full end-to-end agent integration tests
