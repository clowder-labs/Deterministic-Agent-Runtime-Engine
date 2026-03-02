## ADDED Requirements

### Requirement: Headless mode is an explicit non-interactive execution path
The system SHALL expose headless orchestration as an explicit CLI mode for non-interactive execution.

- Headless mode MUST be entered explicitly rather than inferred from legacy `--output json`.
- Headless mode MUST NOT emit prompt-oriented UX such as `dare>` or inline approval prompts.
- `chat` MUST remain interactive and MUST reject headless-only flags.

#### Scenario: Host starts a headless run without prompt UX
- **GIVEN** the host starts `client run` or `client script` in headless mode
- **WHEN** the task begins execution
- **THEN** the client emits structured protocol frames instead of prompt text
- **AND** no inline approval input is requested from the terminal

#### Scenario: Invalid flag combinations are rejected deterministically
- **GIVEN** a caller combines headless-only execution with incompatible legacy output flags
- **WHEN** argument parsing runs
- **THEN** the client exits with a deterministic parameter error
- **AND** it does not silently fall back to interactive or legacy automation output

### Requirement: Headless event envelope v1 is versioned and distinct from legacy automation JSON
The system SHALL emit a versioned event envelope for headless mode that is distinct from the current legacy automation JSON schema.

- Each headless frame MUST include `schema_version`, correlation metadata, an event name, and structured event data.
- The envelope MUST provide stable event ordering semantics within a run.
- Legacy automation JSON MUST remain available without requiring hosts to parse the headless envelope.

#### Scenario: Host receives correlated versioned frames
- **GIVEN** a host consumes headless stdout from a running client session
- **WHEN** lifecycle, tool, or approval-pending events are emitted
- **THEN** each frame includes a version identifier and correlation fields for the active run
- **AND** the host can order frames without parsing human-readable log strings

#### Scenario: Approval demand fails structurally before Slice C
- **GIVEN** a headless session reaches an approval gate before an external control plane is available
- **WHEN** the client cannot resolve the approval interactively
- **THEN** the client reports the condition through structured protocol output
- **AND** the session ends with a non-zero failure instead of prompting for terminal input
