## ADDED Requirements

### Requirement: Transport domain provides agent-facing and client-facing contracts
The system SHALL define a transport domain that exposes a client-facing adapter contract (`ClientChannel`) and an agent-facing interaction contract (`AgentChannel`).

#### Scenario: Agent builds a channel from a client adapter
- **WHEN** a developer provides a `ClientChannel`
- **THEN** the system can construct an `AgentChannel` that the agent uses for `poll`/`send`

### Requirement: Transport envelope is content-agnostic and distinct from context messages
The system SHALL define a `TransportEnvelope` type that is independent from `context.Message` and can carry arbitrary payloads with minimal metadata.

#### Scenario: Envelope carries a control interrupt
- **WHEN** a client sends a `TransportEnvelope` with `kind="control"` and `type="interrupt"`
- **THEN** the agent can observe the interrupt through `AgentChannel.poll()`

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

### Requirement: Interruptible execution helper
The system SHALL provide `AgentChannel.run_interruptible(...)` and `AgentChannel.interrupt()` to cancel the current task.

#### Scenario: Interrupt cancels a running task
- **WHEN** the agent calls `interrupt()` while a task is running via `run_interruptible(...)`
- **THEN** the task is cancelled and the channel clears its current task reference

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
