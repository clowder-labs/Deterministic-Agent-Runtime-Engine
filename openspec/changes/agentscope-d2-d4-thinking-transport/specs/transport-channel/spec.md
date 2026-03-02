## MODIFIED Requirements

### Requirement: Envelope kind supports message, action, and control categories
The transport envelope model SHALL provide a primary categorization field for inbound/outbound envelopes that can distinguish:
- `message` (prompt/result/hook style messages)
- `action` (deterministic resource actions)
- `control` (interrupt/pause/retry/reverse)

For `kind="control"`, implementations SHALL represent control variants via the payload value (e.g. `payload="interrupt"`).
The envelope model MUST NOT require a separate subtype field (e.g. `type`) in order to route inbound envelopes.

For `kind="message"`, implementations SHALL support canonical `event_type` values `message|tool_call|tool_result|thinking|error|status` so intermediate model/tool progress can be delivered without prompt parsing.

#### Scenario: Action envelope is distinguishable without slash parsing
- **GIVEN** a client sends `TransportEnvelope(kind="action", payload="tools:list")`
- **WHEN** the channel receives it
- **THEN** the channel can route it deterministically without inspecting prompt text

#### Scenario: Message envelope carries canonical intermediate event type
- **GIVEN** a runtime emits `TransportEnvelope(kind="message", event_type="tool_call")`
- **WHEN** the envelope is processed by transport consumers
- **THEN** consumers can classify it as a tool invocation intermediate event without content heuristics
