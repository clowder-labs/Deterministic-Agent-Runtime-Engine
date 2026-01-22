## MODIFIED Requirements
### Requirement: Five-Layer Runtime Orchestration
The runtime SHALL implement the five-layer loop (Session, Milestone, Plan, Execute, Tool) as an explicit Kernel contract via `ILoopOrchestrator`, and SHALL expose a tick-based run surface via `IRunLoop` as defined in `doc/design/archive/Architecture_Final_Review_v2.0.md`.

#### Scenario: Execute loop returns to Milestone loop on plan tool
- **WHEN** the Execute Loop encounters a Plan Tool / re-plan trigger
- **THEN** control returns to the Milestone Loop and a new Plan Loop begins without leaking invalid plan state

#### Scenario: Tool loop enforces DonePredicate and budget
- **WHEN** a Tool Loop is started with an `Envelope` containing a `DonePredicate` and `Budget`
- **THEN** the Tool Loop retries until the predicate is satisfied or the budget is exhausted

### Requirement: Plan Attempt Isolation
Plan Loop attempts that fail validation SHALL NOT mutate the outer Milestone state; only validated plans and/or reflections SHALL be persisted to the outer loop state.

#### Scenario: Invalid plan does not leak
- **WHEN** a plan attempt fails validation
- **THEN** the Milestone context excludes invalid plan steps and only retains reflection + audit events

## ADDED Requirements

### Requirement: HITL Gate Between Plan and Execute
The Kernel SHALL place the human approval gate between Plan and Execute, using `ISecurityBoundary.check_policy()` and `IExecutionControl.pause()/resume()` semantics as defined in v2.0.

#### Scenario: Plan requires approval
- **WHEN** `ISecurityBoundary.check_policy(action="execute_plan", ...)` returns `APPROVE_REQUIRED`
- **THEN** the Kernel pauses via `IExecutionControl.pause()` and resumes only after an explicit resume signal

## MODIFIED Requirements

### Requirement: Auditable Event Logging
The Kernel SHALL append structured events to `IEventLog` for state transitions, plan attempts, tool invocations, policy decisions, and verification outcomes, including correlation identifiers (task/session/milestone/run).

#### Scenario: Tool invocation is logged
- **WHEN** `IToolGateway.invoke()` is called
- **THEN** an event is appended to `IEventLog` including capability id, derived risk, decision, and outcome
