## ADDED Requirements
### Requirement: Tool approval memory gates approval-required capabilities
The runtime SHALL evaluate approval-required tool invocations against a trusted approval memory before invoking the tool.

- If an allow rule matches, the invocation SHALL proceed without repeated approval prompts.
- If a deny rule matches, the invocation SHALL be rejected without invoking the tool.
- If no rule matches, the runtime SHALL create a pending approval request and wait for an explicit grant/deny decision.

#### Scenario: Repeated approved invocation is auto-allowed
- **GIVEN** a prior approval rule exists for capability `run_command` with a matching invocation matcher
- **WHEN** the model requests the same invocation again
- **THEN** the runtime invokes the tool directly
- **AND** no new approval request is created

#### Scenario: No rule creates pending approval
- **GIVEN** a capability marked `requires_approval=true`
- **AND** no allow/deny rule matches the invocation
- **WHEN** the tool loop evaluates the invocation
- **THEN** the runtime records a pending approval request and waits for resolution before invoking the tool

#### Scenario: Deny rule blocks invocation
- **GIVEN** a deny rule matches an approval-required invocation
- **WHEN** the tool loop evaluates the invocation
- **THEN** the runtime returns a denied result
- **AND** the tool is not executed

### Requirement: Approval rules support deterministic scope and matching strategies
The runtime SHALL support deterministic approval rule scopes (`once`, `session`, `workspace`, `user`) and matcher strategies (`capability`, `exact_params`, `command_prefix`).

#### Scenario: Command prefix rule applies to matching command
- **GIVEN** an allow rule for `run_command` with matcher `command_prefix="git status"`
- **WHEN** the model requests `run_command` with command `git status --short`
- **THEN** the invocation matches and is auto-approved
