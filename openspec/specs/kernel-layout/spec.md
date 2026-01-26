# kernel-layout Specification

## Purpose
TBD - created by archiving the prior core-domain-layout change. Update Purpose after archive.
## Requirements
### Requirement: Kernel defaults are domain-owned
The system SHALL locate default implementations within the domain `internal/` directory that owns the corresponding contract and SHALL NOT centralize defaults under a cross-domain runtime package.

#### Scenario: Default implementations live with their contracts
- **WHEN** a developer looks for the default event log implementation
- **THEN** it is located under `dare_framework3_3/event/internal/`.

### Requirement: Layer 0 must not depend on Layer 2
Kernel interfaces in `dare_framework3_3/<domain>/kernel.py` SHALL NOT import from `dare_framework3_3/<domain>/component.py` or `dare_framework3_3/<domain>/internal/**`. Shared capability contracts required by kernel defaults SHALL live under the domain `types.py` modules.

#### Scenario: Kernel remains isolated
- **WHEN** a contributor inspects a `kernel.py`
- **THEN** it contains only stable interface definitions and avoids component or implementation imports.

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

### Requirement: Kernel and component interfaces are separated per domain
Each domain package SHALL define kernel interfaces in `kernel.py` and pluggable component interfaces in `component.py` to make Layer 0 vs Layer 2 boundaries explicit.

#### Scenario: Context domain interface split
- **WHEN** a contributor inspects `dare_framework3_3/context/`
- **THEN** kernel interfaces are defined in `kernel.py` and component interfaces are defined in `component.py`.

