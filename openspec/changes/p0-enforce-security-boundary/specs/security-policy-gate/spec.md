## ADDED Requirements

### Requirement: Tool invocation MUST pass security preflight
The runtime SHALL execute security preflight before any side-effecting capability invocation.

- Preflight MUST execute in strict order: `verify_trust` then `check_policy`.
- The runtime MUST NOT call `IToolGateway.invoke(...)` when preflight has not completed.
- Preflight failures MUST produce deterministic denial responses.

#### Scenario: Allowed invocation passes preflight
- **GIVEN** a tool invocation with trusted metadata derivable from registry
- **WHEN** `verify_trust` succeeds and `check_policy` returns `ALLOW`
- **THEN** the runtime invokes the tool through `IToolGateway.invoke(...)`

#### Scenario: Denied invocation is blocked before tool gateway
- **GIVEN** a tool invocation where `check_policy` returns `DENY`
- **WHEN** the runtime evaluates preflight
- **THEN** the runtime rejects the invocation
- **AND** `IToolGateway.invoke(...)` is not called

### Requirement: Policy decisions MUST map to deterministic runtime actions
The runtime SHALL map policy decisions to deterministic control flow.

- `ALLOW` MUST continue invocation immediately.
- `APPROVE_REQUIRED` MUST enter approval flow and wait for resolution.
- `DENY` MUST terminate invocation with a policy denial result.

#### Scenario: APPROVE_REQUIRED routes into approval flow
- **GIVEN** `check_policy` returns `APPROVE_REQUIRED`
- **WHEN** the runtime handles the decision
- **THEN** it creates or reuses an approval request and waits for explicit allow/deny

### Requirement: Security preflight MUST be auditable
The runtime SHALL append structured security events for trust derivation and policy decisions.

- Events MUST include `capability_id`, decision status, and correlation identifiers.
- If approval is required, events MUST include a stable `request_id`.

#### Scenario: Security event payload includes correlation fields
- **WHEN** a policy decision is made for a tool invocation
- **THEN** an event record includes `task_id`, `run_id`, `capability_id`, and decision outcome

