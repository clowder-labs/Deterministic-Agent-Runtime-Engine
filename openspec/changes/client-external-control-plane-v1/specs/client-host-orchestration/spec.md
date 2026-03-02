## MODIFIED Requirements

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

## ADDED Requirements

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
