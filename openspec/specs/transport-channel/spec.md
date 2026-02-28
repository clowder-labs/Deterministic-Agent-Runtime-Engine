# transport-channel Specification

## Purpose
TBD - created by archiving change add-transport-channel. Update Purpose after archive.
## Requirements
### Requirement: Transport domain provides agent-facing and client-facing contracts
The system SHALL define a transport domain that exposes a client-facing adapter contract (`ClientChannel`) and an agent-facing interaction contract (`AgentChannel`).

#### Scenario: Agent builds a channel from a client adapter
- **WHEN** a developer provides a `ClientChannel`
- **THEN** the system can construct an `AgentChannel` that the agent uses for `poll`/`send`

### Requirement: Transport envelope is content-agnostic and distinct from context messages
The system SHALL define a `TransportEnvelope` type that is independent from `context.Message` and can carry arbitrary payloads with minimal metadata.

- The envelope MUST provide a primary strong-typed `kind` categorization that can distinguish `message|action|control`.
- For `kind="action"`, the payload MUST be a deterministic action id string in `resource:action` form (e.g. `tools:list`).
- For `kind="control"`, the payload MUST be a deterministic runtime control id string from `AgentControl` (e.g. `interrupt|pause|retry|reverse`).
- The envelope model MUST NOT require a separate subtype field (e.g. `type`) in order to route inbound envelopes.

#### Scenario: Envelope carries a control interrupt
- **WHEN** a client sends a `TransportEnvelope` with `kind="control"` and `payload="interrupt"`
- **THEN** the channel can route it to control handling without relying on prompt parsing

### Requirement: Channel routes inbound envelopes by kind before agent consumption
The system SHALL route inbound envelopes by `kind` in the channel implementation.

- `kind="message"` envelopes MUST be enqueued to inbox and returned by `poll()`.
- `kind="action"` envelopes MUST be dispatched to action handler infrastructure.
- `kind="control"` envelopes MUST be dispatched to control handler infrastructure.
- If action/control handler bindings are missing at startup, runtime MUST fail fast with configuration error.

#### Scenario: Action envelope does not enter message inbox
- **GIVEN** a channel receives `TransportEnvelope(kind="action", payload="tools:list")`
- **WHEN** inbound routing is applied
- **THEN** the channel invokes action handling path
- **AND** `AgentChannel.poll()` does not return that action envelope

#### Scenario: Missing handler bindings fail at startup
- **GIVEN** runtime starts with channel missing action dispatcher or control handler
- **WHEN** `BaseAgent.start()` runs startup validation
- **THEN** startup fails with explicit configuration error
- **AND** runtime does not enter poll loop

### Requirement: Transport uses queue-based pumping to avoid stack penetration
The system SHALL deliver messages via inbox/outbox queues and a pump task, so that send/receive does not execute user callbacks on the caller stack.

#### Scenario: Agent send does not call client receiver inline
- **WHEN** the agent calls `AgentChannel.send(...)`
- **THEN** the message is enqueued and delivered by a pump task rather than an inline receiver call

### Requirement: Blocking backpressure is the MVP default
The system SHALL apply blocking backpressure when inbox or outbox queues are full.

#### Scenario: Inbox is full
- **WHEN** a client attempts to send to a full inbox
- **THEN** the send blocks until capacity is available

### Requirement: Start/stop lifecycle is defined for the agent channel
The system SHALL provide `start()` and `stop()` on `AgentChannel`, where `start()` is idempotent and `stop()` permits dropping pending outgoing messages.

#### Scenario: Start is called multiple times
- **WHEN** `AgentChannel.start()` is invoked more than once
- **THEN** it does not create duplicate pump tasks

### Requirement: Receiver/sender errors are non-fatal
The system SHALL swallow receiver/sender exceptions and log them without stopping the channel.

#### Scenario: Client receiver raises an exception
- **WHEN** the receiver throws during message delivery
- **THEN** the channel logs the error and continues pumping subsequent messages

### Requirement: Streaming envelope fields are optional but ordered
The system SHALL support optional `stream_id` and `seq` fields on `TransportEnvelope`, where `seq` is monotonically increasing per stream when provided.

#### Scenario: Streaming messages preserve order
- **WHEN** a stream emits envelopes with `stream_id` and increasing `seq`
- **THEN** the agent receives them in queue order without reordering

### Requirement: Agent channel supports optional envelope encoding and decoding
The system SHALL allow `AgentChannel` construction with optional encoder/decoder functions that transform envelopes at the agent boundary.

#### Scenario: Encoder/decoder are applied
- **WHEN** an `AgentChannel` is built with encoder and decoder functions
- **THEN** outgoing envelopes are passed through the encoder and incoming envelopes through the decoder before being exposed to the agent

### Requirement: Transport action channel exposes approval operations
The transport action path SHALL expose deterministic approval operations for runtime clients:
- `approvals:list`
- `approvals:grant`
- `approvals:deny`
- `approvals:revoke`

These operations SHALL be handled without entering the model prompt execution path.

#### Scenario: List pending approvals and rules
- **GIVEN** the runtime has at least one pending approval request
- **WHEN** the client sends action `approvals:list`
- **THEN** the response includes pending approvals and active approval rules

#### Scenario: Grant resolves pending approval
- **GIVEN** a pending approval request id exists
- **WHEN** the client sends action `approvals:grant` with that request id and a rule scope
- **THEN** the pending request is resolved as approved
- **AND** a corresponding rule is created according to the requested scope

#### Scenario: Deny resolves pending approval
- **GIVEN** a pending approval request id exists
- **WHEN** the client sends action `approvals:deny` with that request id
- **THEN** the pending request is resolved as denied

#### Scenario: Revoke removes persisted rule
- **GIVEN** an existing approval rule id
- **WHEN** the client sends action `approvals:revoke` with that rule id
- **THEN** the rule is removed from active approval memory

### Requirement: Envelope kind supports message, action, and control categories
The transport envelope model SHALL provide a primary categorization field for inbound/outbound envelopes that can distinguish:
- `message` (prompt/result/hook style messages)
- `action` (deterministic resource actions)
- `control` (interrupt/pause/retry/reverse)

For `kind="control"`, implementations SHALL represent control variants via the payload value (e.g. `payload="interrupt"`).
The envelope model MUST NOT require a separate subtype field (e.g. `type`) in order to route inbound envelopes.

#### Scenario: Action envelope is distinguishable without slash parsing
- **GIVEN** a client sends `TransportEnvelope(kind="action", payload="tools:list")`
- **WHEN** the channel receives it
- **THEN** the channel can route it deterministically without inspecting prompt text

### Requirement: Agent loop consumes prompt messages only
The runtime integration with `AgentChannel.poll()` SHALL treat polled envelopes as prompt message workload only.

- Agent execution loop MUST NOT be responsible for routing `action` or `control`.
- Any non-message envelope reaching the agent loop MUST be treated as routing error.

#### Scenario: Non-message envelope is rejected in agent loop
- **GIVEN** a non-message envelope is observed in the agent loop
- **WHEN** runtime validation executes
- **THEN** runtime returns an error response
- **AND** does not invoke prompt execution

### Requirement: Entry adapters provide deterministic envelope kinds
Client entry adapters SHALL normalize input into explicit envelope kinds before transport routing.

- `stdio` adapters MAY map slash commands to structured `ACTION/CONTROL` envelopes.
- `websocket` and `A2A` adapters MUST send explicit `kind` and structured `payload`; they MUST NOT rely on slash text inference inside transport runtime.

#### Scenario: Websocket sends explicit action envelope
- **GIVEN** a websocket client wants tool introspection
- **WHEN** it sends `kind="action"` and `payload="tools:list"`
- **THEN** channel routes the request through action path without text parsing
