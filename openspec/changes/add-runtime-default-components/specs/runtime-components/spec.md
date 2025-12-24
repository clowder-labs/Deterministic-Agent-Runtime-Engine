## ADDED Requirements
### Requirement: Default event log
The system SHALL provide a default in-memory event log that records appended events and supports querying by type, milestone, and time range.

#### Scenario: Append and query events
- **WHEN** an event is appended to the event log
- **THEN** a subsequent query returns the event in insertion order

### Requirement: Default checkpoint
The system SHALL provide a default checkpoint that persists runtime state, milestone summaries, and session summaries in memory.

#### Scenario: Save and load milestone summary
- **WHEN** a milestone summary is saved
- **THEN** loading that milestone returns the same summary

### Requirement: Default policy engine
The system SHALL provide a default policy engine that allows tool access and does not require HITL approval unless configured.

#### Scenario: Approval not required
- **WHEN** the default policy engine is used without configuration
- **THEN** milestone plans proceed without pausing for approval

### Requirement: Default plan generator
The system SHALL provide a default plan generator that emits a minimal plan from milestone input.

#### Scenario: Minimal plan
- **WHEN** the plan generator receives a milestone
- **THEN** it returns a plan description with at least one proposed step

### Requirement: Default validator
The system SHALL provide a default validator that validates plan steps and verifies milestone completion permissively.

#### Scenario: Validate plan
- **WHEN** proposed steps refer to registered tools
- **THEN** the validator returns a valid plan

### Requirement: Default remediator
The system SHALL provide a default remediator that returns a reflection summary for failed verification.

#### Scenario: Remediation text
- **WHEN** verification fails
- **THEN** the remediator returns a non-empty reflection string

### Requirement: Default context assembler
The system SHALL provide a default context assembler that packages milestone description, reflections, and prior summaries.

#### Scenario: Assemble context
- **WHEN** assemble is invoked for a milestone
- **THEN** it returns a context object containing milestone description and reflections

### Requirement: Default tool runtime
The system SHALL provide a default tool runtime that invokes registered tools and returns ToolResult responses.

#### Scenario: Invoke registered tool
- **WHEN** the tool runtime is asked to invoke a registered tool
- **THEN** it executes the tool and returns its ToolResult

### Requirement: Default model adapter
The system SHALL provide a default model adapter that returns deterministic responses for testing.

#### Scenario: Deterministic response
- **WHEN** the model adapter is invoked with messages
- **THEN** it returns a response with no tool calls and a fixed message
