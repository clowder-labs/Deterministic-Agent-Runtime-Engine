## ADDED Requirements
### Requirement: Session loop orchestration
The system SHALL execute a Session loop that plans milestones, executes them sequentially, and produces a SessionSummary that is persisted via the checkpoint interface.

#### Scenario: Skip completed milestone on resume
- **WHEN** the checkpoint reports a milestone as completed
- **THEN** the system loads the stored MilestoneSummary and skips re-execution

### Requirement: Milestone loop closed-loop control
The system SHALL execute Milestone loops with Observe → Plan → Approve → Execute → Verify → Remediate, using a budget to prevent infinite retries and returning a MilestoneResult with completeness and termination_reason.

#### Scenario: Verify passes
- **WHEN** verification passes for a milestone
- **THEN** the system returns a MilestoneResult with termination_reason set to `verify_pass`

### Requirement: Plan loop validation and logging
The system SHALL iteratively generate and validate plans until a valid plan is produced or the plan budget is exceeded, and it SHALL log validation failures to the event log.

#### Scenario: Validation failure and retry
- **WHEN** a proposed plan fails validation
- **THEN** the system records a PlanValidationFailedEvent and retries until budget exhaustion

### Requirement: Execute loop tool handling
The system SHALL route tool calls through the tool runtime, capture successful tool evidence, and treat plan tools as a signal to re-enter the Milestone loop.

#### Scenario: Plan tool encountered
- **WHEN** the model requests a plan tool during execution
- **THEN** the execute loop returns an ExecuteResult with `encountered_plan_tool = True`

### Requirement: HITL approval gating
The system SHALL pause execution and wait for resume when the policy engine indicates approval is required for a milestone plan.

#### Scenario: Approval required
- **WHEN** PolicyEngine.needs_approval returns true for a validated plan
- **THEN** the runtime transitions to PAUSED and waits for resume before executing

### Requirement: WorkUnit tool loop completion
The system SHALL enforce Envelope and DonePredicate constraints for WorkUnit tools and raise a ToolExecutionError when completion conditions cannot be met within budget.

#### Scenario: DonePredicate satisfied
- **WHEN** the DonePredicate evaluates to satisfied
- **THEN** the tool loop returns a successful ToolResult
