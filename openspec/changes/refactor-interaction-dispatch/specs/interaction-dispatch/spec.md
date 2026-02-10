## ADDED Requirements

### Requirement: Action dispatch is isolated from control and prompt execution
The system SHALL provide an `ActionHandlerDispatcher` dedicated to deterministic action routing only.

- `ActionHandlerDispatcher` MUST route only `resource:action` requests.
- `ActionHandlerDispatcher` MUST NOT parse prompt messages or handle runtime control signals.
- Action dispatch MUST be driven by stable `ResourceAction` identifiers.

#### Scenario: Action dispatcher ignores control responsibility
- **GIVEN** a runtime control signal such as `interrupt`
- **WHEN** the interaction layer handles the signal
- **THEN** the control path does not call `ActionHandlerDispatcher`
- **AND** action dispatcher remains responsible only for action ids

### Requirement: Action handlers are discoverable and dispatch deterministically
The system SHALL provide a registry that allows domains to register deterministic handlers for `action` inputs.

- Each handler MUST declare which `(resource, action)` pairs it supports.
- For a given `(resource, action)` request, the dispatch MUST select exactly one handler or return a clear error response.

#### Scenario: Resource action routes to a single handler
- **GIVEN** two registered handlers where only one supports `(resource="tools", action="list")`
- **WHEN** an action request for `tools:list` is received
- **THEN** the dispatcher invokes the matching handler
- **AND** it does not invoke non-matching handlers

### Requirement: Deterministic action/control responses are correlated to requests
For deterministic action/control handling, the system SHALL emit responses correlated to the originating request.

- The response `TransportEnvelope.reply_to` MUST be set to the request envelope `id` when available.

#### Scenario: Response sets reply_to
- **GIVEN** an action/control request envelope with `id="req-123"`
- **WHEN** the handler completes successfully
- **THEN** the system sends a response envelope with `reply_to="req-123"`

### Requirement: Deterministic handler errors use a unified payload schema
The system SHALL return deterministic action/control/message errors using a unified payload structure aligned with `TransportEnvelope`.

- Successful payloads MUST include `kind`, `target`, `ok=true`, and `resp` (dict).
- Error payloads MUST include `kind`, `target`, `ok=false`, and `resp` with `code` and `reason`.
- Unsupported action operations MUST use `resp.code="UNSUPPORTED_OPERATION"`.

#### Scenario: Action timeout returns structured error
- **GIVEN** an action request exceeds configured timeout
- **WHEN** the runtime returns an error response
- **THEN** the payload includes `code="ACTION_TIMEOUT"`
- **AND** `reply_to` points to the request id

### Requirement: Standard runtime control signals are provided and dispatchable
The system SHALL provide a stable set of runtime control signals (`AgentControl`) for deterministic interaction handling:
- `interrupt`
- `pause`
- `retry`
- `reverse`

The interaction layer MUST NOT invoke the agent LLM execution path for control signals.
Runtime control signals MUST be routed to a deterministic control handling path (e.g. `ControlHandler`).

#### Scenario: Pause is not executed as a prompt
- **GIVEN** an inbound control envelope with `kind="control"` and `payload="pause"`
- **WHEN** the interaction layer processes the envelope
- **THEN** it does not invoke the LLM-driven agent execution path

### Requirement: Control handling is performed by a dedicated control handler
The system SHALL provide a dedicated `AgentControlHandler` for runtime controls.

- `AgentControlHandler` MUST map `AgentControl` values to agent control methods.
- Control handling MUST NOT require registering control handlers in `ActionHandlerDispatcher`.
- `interrupt` MUST cancel the current execution operation owned by agent runtime.

#### Scenario: Interrupt maps to agent control path
- **GIVEN** an inbound control envelope with `payload="interrupt"`
- **WHEN** control handling executes
- **THEN** the runtime invokes the agent interrupt method
- **AND** the current execution operation is cancelled

### Requirement: Action handling has bounded execution time
The system SHALL enforce a timeout for action handler execution in a single session runtime.

- Action execution timeout MUST be configurable.
- On timeout, runtime MUST terminate the action attempt and return structured error payload.

#### Scenario: Long action is terminated by timeout
- **GIVEN** an action handler execution exceeds timeout
- **WHEN** timeout is reached
- **THEN** runtime terminates the action attempt
- **AND** runtime returns `type="error"` with timeout code

### Requirement: Standard action identifiers are provided for core interaction domains
The system SHALL provide a stable set of standard action identifiers for deterministic interaction handling in the following initial domains:
- `config`
- `tools`
- `mcp`
- `skills`
- `model`
- `actions`

Action identifiers MUST be expressible as `(resource, action)` pairs and SHOULD be representable as a stable enum or registry so handlers and clients can avoid free-form string drift.

#### Scenario: Tools list action uses a stable identifier
- **GIVEN** a client wants to request tool introspection without invoking the agent LLM path
- **WHEN** it sends an action request for `tools:list`
- **THEN** the dispatcher routes the request through the deterministic action handling path
- **AND** the request can be matched by handlers without relying on parsing natural language

### Requirement: Registered actions are discoverable for clients
The system SHALL provide a deterministic action discovery operation.

- `actions:list` MUST return all currently registered action identifiers for the active channel/dispatcher.
- Client adapters MAY map `/` to `actions:list` for command discovery.

#### Scenario: Slash root returns available actions
- **GIVEN** a stdio client sends `/`
- **WHEN** adapter maps it to action `actions:list`
- **THEN** the runtime returns a deterministic list of supported action ids
