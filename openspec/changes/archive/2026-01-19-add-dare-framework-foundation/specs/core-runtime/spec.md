## ADDED Requirements
### Requirement: Five-Layer Runtime Orchestration
The runtime SHALL orchestrate the five-layer loop (Session, Milestone, Plan, Execute, Tool) as defined in `doc/design/archive/Architecture_Final_Review_v1.3.md`, delegating to IPlanGenerator, IValidator, IPolicyEngine, IToolRuntime, and IRemediator.

#### Scenario: Execute encounters a Plan Tool
- **WHEN** the Execute Loop encounters a tool classified as a Plan Tool
- **THEN** execution stops and control returns to the Milestone Loop to re-plan

#### Scenario: Tool Loop enforces DonePredicate
- **WHEN** a WorkUnit tool is invoked with an Envelope containing a DonePredicate
- **THEN** the Tool Loop retries until the DonePredicate is satisfied or budget is exhausted

### Requirement: Runtime State Machine
IRuntime SHALL expose init/run/pause/resume/stop/cancel with state transitions defined in v1.3, and SHALL report the current RuntimeState.

#### Scenario: Pause and resume
- **WHEN** pause() is called while running
- **THEN** the runtime transitions to PAUSED and can later resume() to RUNNING

### Requirement: Auditable Event Logging
The runtime SHALL append structured events to IEventLog for state transitions, plan attempts, tool invocations, and verification outcomes.

#### Scenario: State transition is logged
- **WHEN** the runtime transitions from READY to RUNNING
- **THEN** an event is appended to IEventLog describing the transition

### Requirement: Checkpointing and Recovery
The runtime SHALL integrate ICheckpoint to persist state during pause/cancel paths and support resuming from a prior checkpoint.

#### Scenario: Pause creates a checkpoint
- **WHEN** pause() is invoked during an active session
- **THEN** a checkpoint is saved and is usable for resume()

### Requirement: Plan Attempt Isolation
Plan Loop attempts that fail validation SHALL NOT mutate Milestone context; only validated plans or reflections may be persisted to the outer loop state.

#### Scenario: Invalid plan does not leak
- **WHEN** a plan attempt fails validation
- **THEN** the Milestone context excludes the invalid plan steps and only retains the reflection
