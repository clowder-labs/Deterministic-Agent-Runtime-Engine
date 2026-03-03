# client-host-orchestration Specification

## Purpose
Define the stable host-orchestration contract for `client/`, including explicit mode separation, headless event semantics, the planned structured local control plane, and capability discovery boundaries.
## Requirements
### Requirement: Client host orchestration modes are explicitly separated
The system SHALL distinguish between interactive CLI behavior, legacy automation JSON output, and host-orchestrated headless execution.

- Interactive mode MAY use prompts and inline human approval UX.
- Legacy automation JSON MAY keep the current `log/event/result` line schema for backward compatibility.
- Headless host orchestration MUST be an explicit mode boundary and MUST NOT rely on prompt text or inline human approval interactions.
- `chat` MUST remain interactive and MUST reject headless-only flags.
- Incompatible headless/legacy flag combinations MUST fail with a deterministic parameter error instead of silently falling back.

#### Scenario: Headless mode does not depend on prompt UX
- **GIVEN** the client is started in host-orchestrated headless mode
- **WHEN** a task execution requires runtime observation or control
- **THEN** the client does not emit `dare>` style prompts
- **AND** it does not require inline approval input from stdout/stdin prompt UX

#### Scenario: Invalid flag combinations are rejected deterministically
- **GIVEN** a caller combines headless-only execution with incompatible legacy output flags
- **WHEN** argument parsing runs
- **THEN** the client exits with a deterministic parameter error
- **AND** it does not silently fall back to interactive or legacy automation output

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

- v1 MUST support a local `--control-stdin` entry for headless `run/script`.
- The control plane MUST accept deterministic actions for approvals, MCP management, skills discovery, and session status.
- Control responses MUST use structured success/error payloads with request correlation.
- The control plane MUST preserve existing approval and action semantics rather than bypassing them.

#### Scenario: Host grants approval through structured control
- **GIVEN** a running headless session emits an approval-pending event
- **WHEN** the host submits a structured approval grant command
- **THEN** the client resolves the approval through the deterministic approval action path
- **AND** the result is returned as a structured control response

#### Scenario: Unknown control action fails structurally
- **GIVEN** a host sends a control command with an unsupported action id
- **WHEN** the client validates the command frame
- **THEN** the client returns a structured error response
- **AND** it does not fall back to prompt-oriented or natural-language command parsing

### Requirement: Host capabilities are discoverable without hardcoded matrices
The system SHALL provide a deterministic capability discovery surface for host orchestration.

- v1 capability discovery MUST be exposed as an explicit `actions:list` request over the structured local control plane.
- The discovery response MUST return the currently supported canonical action ids as structured data.
- v1 MUST NOT require an unsolicited startup handshake before a host can interact with the session.

#### Scenario: Host queries supported actions over control plane
- **GIVEN** a host is attached to a running headless session through `--control-stdin`
- **WHEN** it sends action `actions:list`
- **THEN** the client returns a structured list of currently supported canonical action ids
- **AND** the host does not need to infer support by parsing help text or natural-language output

#### Scenario: Startup does not emit unsolicited capability handshake
- **GIVEN** a host starts a headless session and has not sent a discovery request
- **WHEN** the session begins running
- **THEN** the client does not emit an unsolicited capability handshake frame
- **AND** capability discovery remains available through an explicit structured request

### Requirement: Control plane v1 reuses canonical action identifiers
The system SHALL expose control-plane actions using canonical stable identifiers.

- MCP control in v1 MUST be limited to `mcp:list`, `mcp:reload`, and `mcp:show-tool`.
- CLI-only verbs without canonical actions, including `mcp:unload`, MUST NOT be advertised as v1 host protocol actions.
- Approvals and skills actions MUST reuse their existing `resource:action` identifiers.

#### Scenario: Host reloads MCP providers through canonical action id
- **GIVEN** the host needs to refresh MCP provider paths for a running headless session
- **WHEN** it sends action `mcp:reload` through the control plane
- **THEN** the client reuses the current MCP reload runtime path
- **AND** the response is returned as a structured control result

#### Scenario: Host requests CLI session status
- **GIVEN** a headless session is running under the CLI host protocol
- **WHEN** the host sends action `status:get`
- **THEN** the client returns a structured snapshot of current session state
- **AND** the response is correlated to the request id

