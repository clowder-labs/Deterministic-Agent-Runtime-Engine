## MODIFIED Requirements
### Requirement: Tool name is the tool call identity
The system SHALL use `ITool.name` as the LLM-facing tool identity. The tool definition MUST use `function.name == ITool.name`. Tool calls SHALL be resolved by tool name to the trusted registry entry and routed using its `capability_id`, which remains the internal stable identifier.

#### Scenario: Tool naming is consistent across LLM and routing
- **GIVEN** a tool registered with `name` "read_file" and `capability_id` "tool_123"
- **WHEN** the tool is exposed to the model
- **THEN** the tool definition name equals "read_file" and includes `capability_id` for routing/observability
- **WHEN** the model calls tool name "read_file"
- **THEN** the runtime resolves it to `capability_id` "tool_123" before invoking the gateway

## ADDED Requirements
### Requirement: Tool names are globally unique
The tool registry SHALL reject duplicate `ITool.name` values across all registered capabilities.

#### Scenario: Duplicate tool names are rejected
- **GIVEN** a tool registry already containing tool name "read_file"
- **WHEN** another tool with name "read_file" is registered or refreshed
- **THEN** registration fails with a clear error and the existing entry remains unchanged
