# Tasks: refactor-interaction-dispatch

## 1. Freeze contracts and boundaries
- [x] 1.1 Confirm `EnvelopeKind` as strong enum and routing key
- [x] 1.2 Confirm channel-side split for `MESSAGE|ACTION|CONTROL`
- [x] 1.3 Confirm `ActionHandlerDispatcher` only handles actions
- [x] 1.4 Confirm `AgentControlHandler` only handles controls

## 2. Transport/channel implementation alignment
- [x] 2.1 Update `TransportEnvelope` typing and validation for enum `kind`
- [x] 2.2 Implement kind-based dispatch in `DefaultAgentChannel._enqueue_inbox`
- [x] 2.3 Ensure channel emits structured error replies for invalid action/control envelopes
- [x] 2.4 Ensure only `MESSAGE` envelopes reach `poll()`/inbox
- [x] 2.5 Enforce unified deterministic error payload fields (`type/kind/target/ok/code/reason`)

## 3. Builder and agent runtime alignment
- [x] 3.1 Build action/control handlers in builder from domain managers
- [x] 3.2 Register handlers into channel during `build()`
- [x] 3.3 Refactor `BaseAgent` loop to process message prompts only
- [x] 3.4 Add startup validation to fail fast when channel lacks handler bindings

## 4. Client adapter alignment
- [x] 4.1 Move slash parsing to stdio adapter (`/resource:action`, `/interrupt`)
- [x] 4.2 Keep `/quit` and `/exit` as client lifecycle commands (non-transport)
- [x] 4.3 Map single `/` to action discovery request (`actions:list`)
- [x] 4.4 Enforce websocket/A2A explicit `kind` contract (no slash inference in transport)

## 5. Timeout and runtime guards
- [x] 5.1 Add configurable action timeout for channel-dispatched actions
- [x] 5.2 Return `ACTION_TIMEOUT` structured errors on timeout
- [x] 5.3 Ensure timeout path does not break subsequent message processing

## 6. Tests and verification
- [x] 6.1 Add/adjust channel tests for kind dispatch behavior
- [x] 6.2 Add/adjust dispatcher tests to action-only responsibilities
- [x] 6.3 Add/adjust agent loop tests to message-only consumption
- [x] 6.4 Add timeout tests for long-running action handlers
- [x] 6.5 Run `openspec validate refactor-interaction-dispatch --strict`
- [x] 6.6 Run targeted pytest suites for transport + interaction changes
