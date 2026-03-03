## MODIFIED Requirements

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
