# client-host-orchestration Specification

## Purpose
Define the stable host-orchestration contract for `client/`, including explicit mode separation, headless event semantics, the planned structured local control plane, and capability discovery boundaries.

## Requirements

### Requirement: Client host orchestration modes are explicitly separated
The system SHALL distinguish between interactive CLI behavior, legacy automation JSON output, and host-orchestrated headless execution.

- Interactive mode MAY use prompts and inline human approval UX.
- Legacy automation JSON MAY keep the current `log/event/result` line schema for backward compatibility.
- Headless host orchestration MUST be an explicit mode boundary and MUST NOT rely on prompt text or inline human approval interactions.

#### Scenario: Headless mode does not depend on prompt UX
- **GIVEN** the client is started in host-orchestrated headless mode
- **WHEN** a task execution requires runtime observation or control
- **THEN** the client does not emit `dare>` style prompts
- **AND** it does not require inline approval input from stdout/stdin prompt UX

### Requirement: Headless event envelope v1 is versioned and distinct from legacy automation JSON
The system SHALL emit a versioned event envelope for headless mode that is distinct from the current legacy automation JSON schema.

- Headless mode MUST be entered explicitly rather than inferred from legacy `--output json`.
- Each headless frame MUST include `schema_version`, correlation metadata, an event name, and structured event data.
- The envelope MUST provide stable event ordering semantics within a run.
- Legacy automation JSON MUST remain available without requiring hosts to parse the headless envelope.

#### Scenario: Host starts a headless run without prompt UX
- **GIVEN** the host starts `client run` or `client script` in headless mode
- **WHEN** the task begins execution
- **THEN** the client emits structured protocol frames instead of prompt text
- **AND** no inline approval input is requested from the terminal

#### Scenario: Host receives correlated versioned frames
- **GIVEN** a host consumes headless stdout from a running client session
- **WHEN** lifecycle, tool, or approval-pending events are emitted
- **THEN** each frame includes a version identifier and correlation fields for the active run
- **AND** the host can order frames without parsing human-readable log strings

#### Scenario: Approval demand fails structurally before external control is available
- **GIVEN** a headless session reaches an approval gate before an external control plane is available
- **WHEN** the client cannot resolve the approval interactively
- **THEN** the client reports the condition through structured protocol output
- **AND** the session ends with a non-zero failure instead of prompting for terminal input

### Requirement: Host control is provided through a structured local control plane
The system SHALL provide a structured local control plane for host-orchestrated sessions.

- The control plane MUST accept deterministic actions for approvals, MCP management, skills discovery, and session status.
- Control responses MUST use structured success/error payloads.
- The control plane MUST preserve existing approval and action semantics rather than bypassing them.

#### Scenario: Host grants approval through structured control
- **GIVEN** a running headless session emits an approval-pending event
- **WHEN** the host submits a structured approval grant command
- **THEN** the client resolves the approval through the deterministic approval action path
- **AND** the result is returned as a structured control response

### Requirement: Host capabilities are discoverable without hardcoded matrices
The system SHALL provide a deterministic capability discovery surface for host orchestration.

- Hosts MUST be able to discover supported actions for the active client/runtime.
- Capability discovery MAY be exposed via an explicit action such as `actions:list` or an equivalent startup handshake.

#### Scenario: Host queries supported actions
- **GIVEN** a host needs to determine whether the client supports dynamic MCP reload
- **WHEN** it requests capability discovery
- **THEN** the client returns a structured list of supported actions
- **AND** the host does not need to infer support by parsing help text or natural-language output
