## MODIFIED Requirements
### Requirement: Core Data Models
The interface layer SHALL provide canonical data models, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `Budget`, `ToolDefinition`, `ToolResult`, `ExecutionSignal`, `Checkpoint`, `Task`, `Milestone`, `RunResult`, `Event`, `RuntimeSnapshot`, `HookPhase`, `RiskLevel`, `PolicyDecision`, `TrustedInput`, and `SandboxSpec`.

`ToolResult` SHALL support a typed output payload model so tool output schema can be derived from the declared return type of `ITool.execute(...)`.

#### Scenario: Tool result output typing drives output schema
- **GIVEN** a tool execute method returns `ToolResult[MyOutput]`
- **WHEN** capability metadata is assembled
- **THEN** the capability output schema is derived from `MyOutput`

### Requirement: Tool providers return ITool lists
`IToolProvider` SHALL return tool instances rather than tool definitions. The provider acts only as a tool source for registration into ToolManager.

`ITool.execute(...)` SHALL use keyword-parameter invocation with a required `run_context` argument. Tool input/output schema SHALL be inferred from the `execute` signature and return annotations, with doc comments used for human-readable field descriptions.

#### Scenario: Execute signature is the input contract
- **GIVEN** an `ITool` with execute parameters `path: str` and `limit: int | None = None`
- **WHEN** the capability descriptor is generated
- **THEN** `input_schema.properties` includes `path` and `limit`
- **AND** `path` is required while `limit` is optional

#### Scenario: Parameter comments become field descriptions
- **GIVEN** an `ITool` execute docstring that documents parameter meanings
- **WHEN** the input schema is generated
- **THEN** corresponding schema fields include those descriptions
