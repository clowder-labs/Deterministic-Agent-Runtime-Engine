## MODIFIED Requirements

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

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Interruptible execution helper
**Reason**: 该能力将 transport channel 变成业务执行的“任务宿主”，导致 transport 与交互语义耦合。中断/取消应由交互层（dispatcher/agent）维护当前执行操作并取消，从而保持 transport 的 content-agnostic 边界。

**Migration**:
- 移除 `AgentChannel.run_interruptible(...)` 与 `AgentChannel.interrupt()`。
- 当接收到 `TransportEnvelope(kind="control", payload="interrupt")` 时，由控制处理路径触发 agent 中断并取消当前执行操作。
