## MODIFIED Requirements
### Requirement: Tool manager maintains trusted capability registry
ToolManager SHALL maintain the trusted capability registry for tools. It MUST:
- Register, update, and unregister tool capabilities
- Use `tool.name` as the `capability_id` and reject duplicate names
- Track enable/disable state per capability
- Persist trusted metadata (`risk_level`, `requires_approval`, `timeout_seconds`, `is_work_unit`, `capability_kind`)
- Serve as the source of truth for runtime tool activation

Capability `input_schema` and `output_schema` MUST be derived from each tool's `execute` contract (signature, type annotations, and doc comments for descriptions), rather than manually duplicated schema literals.

#### Scenario: Registry schema follows execute signature
- **GIVEN** a registered tool with explicit execute keyword parameters
- **WHEN** ToolManager builds a capability descriptor
- **THEN** descriptor schemas match execute parameter and return annotations
- **AND** schema field descriptions reflect execute doc comments when provided
