## MODIFIED Requirements

### Requirement: Capability id is the tool call identity
The system SHALL use the tool's `name` as the canonical identity for capabilities. The LLM-facing tool definition MUST use `function.name == tool.name`, and ToolManager/ToolGateway MUST route invocations by this same identifier.

#### Scenario: Tool naming is consistent across LLM and routing
- **GIVEN** a tool registered into ToolManager
- **WHEN** the tool is exposed to the model
- **THEN** the tool definition name equals the tool's `name` and tool calls route by that value

## ADDED Requirements

### Requirement: Tool names are unique in the registry
ToolManager SHALL reject registration of a tool whose `name` collides with an existing capability id.

#### Scenario: Duplicate tool name is rejected
- **GIVEN** a tool named `write_file` is registered
- **WHEN** another tool with name `write_file` is registered
- **THEN** ToolManager rejects the registration with a clear error
