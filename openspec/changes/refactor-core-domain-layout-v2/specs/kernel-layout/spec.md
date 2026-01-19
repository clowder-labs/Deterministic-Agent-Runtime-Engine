## MODIFIED Requirements

### Requirement: Kernel defaults are domain-owned
The system SHALL locate Kernel default implementations within the domain package that owns the corresponding Kernel contract and SHALL NOT centralize defaults under a `dare_framework/core/defaults/` catch-all directory.

#### Scenario: Default implementations live with their contracts
- **WHEN** a developer looks for the default event log implementation
- **THEN** it MUST be located under the `dare_framework/core/event/` domain package (not under a global defaults directory)

### Requirement: Layer 0 must not depend on Layer 2
Kernel code under `dare_framework/core/` SHALL NOT import from `dare_framework/components/`. Shared capability contracts required by Kernel defaults (e.g., memory) SHALL live under `dare_framework/contracts/`.

#### Scenario: Context manager depends only on contracts
- **WHEN** `DefaultContextManager` depends on `IMemory`
- **THEN** it MUST reference `IMemory` from `dare_framework/contracts/` and MUST NOT import `dare_framework/components/*`

### Requirement: Tool Loop separates boundary from invocation payload
`Envelope` SHALL represent only the Tool Loop execution boundary (allow-list, budget, done predicate, risk). Tool invocation payload (capability id and params) SHALL be carried separately (e.g., `ToolLoopRequest`) and passed explicitly into the tool loop.

#### Scenario: Tool loop request carries capability id and params
- **WHEN** the orchestrator runs the Tool Loop
- **THEN** it MUST use a request object containing `capability_id` and `params` plus an `Envelope` that contains only boundary fields

### Requirement: Risk and approval are derived from trusted registries
The system SHALL derive `risk_level` and `requires_approval` from trusted capability registry metadata for policy enforcement, for both plan-driven and model-driven tool calls. The system MUST ignore any risk/approval values provided by untrusted sources (planner/model output).

#### Scenario: Model-driven tool call cannot downgrade risk
- **WHEN** the model calls a tool whose capability descriptor declares a non-READ_ONLY risk level
- **THEN** policy evaluation MUST use the registry-derived risk level and require approval per policy
