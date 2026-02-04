## MODIFIED Requirements

### Requirement: Tool manager maintains trusted capability registry
ToolManager SHALL maintain the trusted capability registry for tools. It MUST:
- Register, update, and unregister tool capabilities
- Use `tool.name` as the `capability_id` and reject duplicate names
- Track enable/disable state per capability
- Persist trusted metadata (`risk_level`, `requires_approval`, `timeout_seconds`, `is_work_unit`, `capability_kind`)
- Serve as the source of truth for runtime tool activation and invocation

#### Scenario: Duplicate tool name is rejected
- **GIVEN** a tool named `write_file` is registered
- **WHEN** another tool with name `write_file` is registered
- **THEN** ToolManager rejects the registration with a clear error
