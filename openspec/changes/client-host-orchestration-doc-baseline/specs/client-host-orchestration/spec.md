## ADDED Requirements

### Requirement: Client host orchestration modes are explicitly separated
The system SHALL distinguish between interactive CLI behavior, legacy automation JSON output, and a future host-orchestrated headless contract.

- Interactive mode MAY use prompts and inline human approval UX.
- Legacy automation JSON MAY keep the current `log/event/result` line schema for backward compatibility.
- Headless host orchestration MUST be an explicit mode boundary and MUST NOT rely on prompt text or inline human approval interactions.

#### Scenario: Headless mode does not depend on prompt UX
- **GIVEN** the client is started in host-orchestrated headless mode
- **WHEN** a task execution requires runtime observation or control
- **THEN** the client does not emit `dare>` style prompts
- **AND** it does not require inline approval input from stdout/stdin prompt UX

### Requirement: Host event stream is versioned and correlated
The system SHALL provide a versioned host event envelope for headless orchestration that is distinct from the legacy automation JSON line schema.

- The envelope MUST include a schema version field.
- The envelope MUST include correlation metadata sufficient for session/run/event ordering.
- The envelope MUST provide stable event identifiers or sequence semantics for host replay and parsing.

#### Scenario: Host receives correlated event frames
- **GIVEN** a host launches the client in headless mode
- **WHEN** the client emits lifecycle, tool, or approval events
- **THEN** each frame contains versioned envelope metadata
- **AND** the host can correlate frames within the same run without parsing human-readable log text

### Requirement: Host control is provided through a structured local control plane
The system SHALL provide a structured local control plane for host-orchestrated sessions.

- The control plane MUST accept deterministic actions for approvals, MCP management, skills discovery, and capability discovery.
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
- Capability discovery MAY be exposed via an explicit action such as `actions.list` or an equivalent startup handshake.

#### Scenario: Host queries supported actions
- **GIVEN** a host needs to determine whether the client supports dynamic MCP reload
- **WHEN** it requests capability discovery
- **THEN** the client returns a structured list of supported actions
- **AND** the host does not need to infer support by parsing help text or natural-language output
