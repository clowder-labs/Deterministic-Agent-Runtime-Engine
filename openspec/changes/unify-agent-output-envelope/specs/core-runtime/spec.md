## ADDED Requirements

### Requirement: Agent RunResult Output Envelope
The runtime SHALL return a normalized output envelope for all primary agent implementations (`SimpleChatAgent`, `ReactAgent`, `DareAgent`) via `RunResult.output`.

The envelope MUST use this schema:
- `content`: `str`
- `metadata`: `dict`
- `usage`: `dict | None`

`RunResult.output_text` MUST remain aligned with `RunResult.output.content`.

#### Scenario: SimpleChatAgent returns normalized envelope
- **WHEN** `SimpleChatAgent.execute(...)` completes successfully
- **THEN** `RunResult.output` is a dict containing `content`, `metadata`, and `usage`
- **AND** `RunResult.output_text` equals `RunResult.output["content"]`

#### Scenario: ReactAgent returns normalized envelope
- **WHEN** `ReactAgent.execute(...)` completes (normal completion or loop-guard completion)
- **THEN** `RunResult.output` is a dict containing `content`, `metadata`, and `usage`
- **AND** `RunResult.output_text` equals `RunResult.output["content"]`

#### Scenario: DareAgent returns normalized envelope
- **WHEN** `DareAgent.execute(...)` completes
- **THEN** `RunResult.output` is a dict containing `content`, `metadata`, and `usage`
- **AND** `RunResult.output_text` equals `RunResult.output["content"]`
