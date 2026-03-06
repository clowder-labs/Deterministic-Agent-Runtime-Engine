## MODIFIED Requirements

### Requirement: Client host orchestration modes are explicitly separated
The system SHALL distinguish between interactive CLI behavior, legacy automation JSON output, and host-orchestrated headless execution.

- Interactive mode MAY use prompts and inline human approval UX.
- Legacy automation JSON MAY keep the current `log/event/result` line schema for backward compatibility.
- Headless host orchestration MUST be an explicit mode boundary and MUST NOT rely on prompt text or inline human approval interactions.
- `chat` MUST remain interactive and MUST reject headless-only flags.
- Incompatible headless/legacy flag combinations MUST fail with a deterministic parameter error instead of silently falling back.
- Any of `chat`, `run`, or `script` MAY explicitly resume a persisted session snapshot without changing the mode boundary semantics above.

#### Scenario: Interactive resume restores prior conversation history
- **GIVEN** a workspace contains a persisted CLI session snapshot
- **WHEN** the user starts `dare chat --resume` or `dare chat --resume <session-id>`
- **THEN** the client restores the prior session id and message history before accepting the next prompt
- **AND** the resumed session starts from an idle CLI state instead of pretending a previous task is still running

#### Scenario: Missing resume target fails deterministically
- **GIVEN** the user passes `--resume latest` or `--resume <session-id>`
- **WHEN** no matching persisted session snapshot exists
- **THEN** the client exits with a deterministic parameter error
- **AND** it does not silently create a fresh empty session

#### Scenario: Session-id compatibility alias maps to resume semantics
- **GIVEN** a persisted CLI session snapshot exists
- **WHEN** the user starts `dare run --session-id <session-id> --task "<task>"`
- **THEN** the client restores the specified session history before task execution
- **AND** it reuses the restored session id as the task conversation id

#### Scenario: Conflicting resume flags are rejected
- **GIVEN** a user passes both `--resume` and `--session-id`
- **WHEN** the two targets are not equal after normalization
- **THEN** the client exits with a deterministic parameter error
- **AND** it does not start runtime task execution

#### Scenario: User lists resumable sessions
- **GIVEN** a workspace contains one or more persisted CLI session snapshots
- **WHEN** the user runs `dare sessions list` or `/sessions list`
- **THEN** the client returns a structured list of resumable session summaries ordered by most recent update
- **AND** each entry includes enough data for the user to choose a `--resume <session-id>` target

#### Scenario: Headless host resumes session through control-stdin
- **GIVEN** a headless `run/script` session is started with `--control-stdin`
- **AND** no task is currently running
- **WHEN** the host sends a `client-control-stdin.v1` frame with action `session:resume` and a valid session id
- **THEN** the client restores the requested session history and returns a structured success frame
- **AND** `actions:list` includes `session:resume` for capability discovery
