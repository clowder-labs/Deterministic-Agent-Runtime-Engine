# interface-layer Specification

## Purpose
TBD - created by archiving the prior plugin-system change. Update Purpose after archive.
## Requirements
### Requirement: Shared types are canonical
The system SHALL locate canonical types within their owning domains (context, tool, plan, event, hook, security, model, memory, config) and SHALL use them across Kernel/components/examples.

#### Scenario: Tool loop returns canonical ToolResult
- **GIVEN** a tool invocation through the Tool Loop
- **WHEN** it completes
- **THEN** the result is represented using the canonical `ToolResult` type.

### Requirement: Core Interface Coverage
The interface layer SHALL define Kernel and Component contracts, including a shared component identity contract (`IComponent`) and the shared `ComponentType` enum.

#### Scenario: Developer imports shared component identity
- **WHEN** a developer implements a pluggable component
- **THEN** they can implement `IComponent` and reference `ComponentType` from the canonical infra module

### Requirement: Core Data Models
The interface layer SHALL provide canonical data models, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `Budget`, `ToolDefinition`, `ToolResult`, `ExecutionSignal`, `Checkpoint`, `Task`, `Milestone`, `RunResult`, `Event`, `RuntimeSnapshot`, `HookPhase`, `RiskLevel`, `PolicyDecision`, `TrustedInput`, and `SandboxSpec`.

`ToolResult` SHALL support a typed output payload model so tool output schema can be derived from the declared return type of `ITool.execute(...)`.

#### Scenario: Tool result output typing drives output schema
- **GIVEN** a tool execute method returns `ToolResult[MyOutput]`
- **WHEN** capability metadata is assembled
- **THEN** the capability output schema is derived from `MyOutput`

### Requirement: AgentBuilder Composition API
The developer-facing agent API SHALL support composing agents via typed builders and deterministic resolution rules:

- The system SHALL provide builder variants for at least:
  - `SimpleChatAgent` (simple chat mode)
  - `FiveLayerAgent` (five-layer orchestration mode)
- Builders SHALL accept explicit component overrides (developer-injected instances) and SHALL treat them as highest precedence.
- When a required component is not explicitly provided, builders SHALL attempt to resolve it via the corresponding domain manager using the effective `Config`.
- For multi-load component categories (e.g., tools/hooks/validators), builders SHALL merge explicit components with manager-loaded components (extend semantics) while preserving injection order.
- Config enable/disable filtering MUST apply only to the manager-loaded subset and MUST NOT remove explicitly injected components.
- Builders SHALL keep `assemble_context` externally injectable so callers can customize `AssembledContext` generation.
- Builders SHALL expose a boolean skill-tool toggle (`_enable_skill_tool` via public builder API) as the only built-in skill mode switch.
- When skill-tool toggle is enabled, builders MUST auto-register `search_skill` and default context assembly MUST ignore `sys_skill`.
- When skill-tool toggle is disabled, builders MUST NOT auto-register `search_skill` and explicit `sys_skill` injection remains effective.

#### Scenario: Skill tool mode auto-registers search tool
- **GIVEN** a builder with skill-tool toggle enabled
- **WHEN** `build()` is called
- **THEN** the built context exposes `search_skill` in tool capabilities
- **AND** default assemble logic does not merge `sys_skill`

#### Scenario: Non skill tool mode preserves explicit sys_skill
- **GIVEN** a builder with skill-tool toggle disabled
- **AND** an explicit `sys_skill` is set on context
- **WHEN** default assemble logic runs
- **THEN** `search_skill` is not auto-registered
- **AND** the assembled system prompt includes the explicit `sys_skill`

#### Scenario: Custom assemble context remains pluggable
- **GIVEN** a caller injects a custom `assemble_context`
- **WHEN** the agent assembles context for model input
- **THEN** the custom strategy is used instead of the default strategy

### Requirement: Optional MCP Integration Surface
The interface layer SHALL NOT define protocol adapter interfaces. Protocol adapter surfaces are deferred until a dedicated integration is specified.

#### Scenario: MCP is not configured
- **WHEN** no MCP clients are provided
- **THEN** the runtime operates with local tools only and does not attempt protocol discovery

### Requirement: Default ToolGateway Aggregates Capability Providers
The canonical `dare_framework` package SHALL provide a default `IToolGateway` implementation (`ToolGateway`) that is backed by `IToolManager` capability state. The gateway MUST enforce envelope allowlists during invocation and MUST resolve tools through the manager registry.

#### Scenario: List capabilities from manager-backed gateway
- **GIVEN** two registered tool providers in the manager
- **WHEN** `ToolGateway.list_capabilities()` is called
- **THEN** it returns the combined capability descriptors without duplicate ids

#### Scenario: Reject disallowed capability invoke
- **GIVEN** an envelope with `allowed_capability_ids` that does not include a requested capability
- **WHEN** `ToolGateway.invoke()` is called
- **THEN** the gateway rejects the request

### Requirement: Manager interfaces are domain-owned
The system SHALL define component manager interfaces alongside their owning domain interfaces, not in the config domain. Specifically:
- Tool manager: `dare_framework/tool/kernel.py`
- Model adapter manager: `dare_framework/model/interfaces.py`
- Planner/validator/remediator managers: `dare_framework/plan/interfaces.py`
- Hook manager: `dare_framework/hook/interfaces.py`

#### Scenario: Tool manager import path
- **WHEN** a contributor imports `IToolManager`
- **THEN** it is available from `dare_framework.tool.kernel` (and re-exported from `dare_framework.tool`) and not from `dare_framework.tool.interfaces`

### Requirement: Tool manager contract
The tool domain SHALL define an `IToolManager` contract in `dare_framework/tool/kernel.py` for trusted tool registration, provider aggregation, and capability metadata export. `IToolManager` SHALL NOT be the invocation boundary and SHALL NOT require `invoke(...)`.

At minimum it MUST include:
- `register_tool(...)`, `unregister_tool(...)`, `update_tool(...)`
- `register_provider(...)`, `unregister_provider(...)`
- `list_capabilities(...)`, `refresh(...)`
- `list_tool_defs(...)`, `get_capability(...)`
- `health_check(...)`

#### Scenario: Tool manager is not used as gateway
- **GIVEN** the default `ToolManager` implementation
- **WHEN** a runtime invocation is needed
- **THEN** invocation flows through `IToolGateway.invoke(...)`
- **AND** the manager is used only for capability lookup and lifecycle state

### Requirement: Builder facade for variant selection
The system SHALL provide a stable facade for selecting which builder variant to use via `BaseAgent`, such as:

- `BaseAgent.simple_chat_agent_builder(name)` → builder for `SimpleChatAgent`
- `BaseAgent.five_layer_agent_builder(name)` → builder for `FiveLayerAgent`

#### Scenario: Developer selects a builder variant
- **WHEN** a developer selects a builder variant via `BaseAgent`
- **THEN** they receive a builder whose `build()` produces the corresponding agent type

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

### Requirement: Capability id is the tool call identity
The system SHALL use the tool's `name` as the canonical identity for capabilities. The LLM-facing tool definition MUST use `function.name == tool.name`, and ToolManager/ToolGateway MUST route invocations by this same identifier.

#### Scenario: Tool naming is consistent across LLM and routing
- **GIVEN** a tool registered into ToolManager
- **WHEN** the tool is exposed to the model
- **THEN** the tool definition name equals the tool's `name` and tool calls route by that value

### Requirement: Trusted tool listings for model prompts
Context and runtime model-input assembly SHALL source tool availability from the trusted capability registry exposed by `IToolGateway.list_capabilities()`; tool listings MUST NOT originate from untrusted sources (planner/model output).

`ModelInput.tools` MUST carry `CapabilityDescriptor` entries. Model adapters are responsible for converting these trusted descriptors into provider-specific tool-definition payloads.

#### Scenario: Context assembles capability descriptors for model adapters
- **GIVEN** context is wired with the default `ToolManager`
- **WHEN** context assembles tool listings for a model request
- **THEN** each item is a `CapabilityDescriptor`
- **AND** adapters can access descriptor fields (`name`, `description`, `input_schema`) without dict coercion

### Requirement: Default model adapter manager fallback
When no explicit model adapter and no model adapter manager are provided, builders SHALL fall back to a default model adapter manager created by the model domain factory and resolve the adapter using the effective `Config`.

#### Scenario: Builder uses default manager
- **GIVEN** a builder with no explicit model adapter
- **AND** no model adapter manager is provided
- **WHEN** `build()` is called
- **THEN** the builder uses the model domain default manager to resolve the adapter using `Config.llm`

### Requirement: BaseAgent is a public agent entry point
The agent domain SHALL expose `BaseAgent` as a public type, and built-in agents SHALL inherit from it.

#### Scenario: Developer imports BaseAgent
- **WHEN** a developer imports `BaseAgent` from `dare_framework.agent`
- **THEN** the import succeeds without referencing `_internal` modules

### Requirement: Tool names are unique in the registry
ToolManager SHALL reject registration of a tool whose `name` collides with an existing capability id.

#### Scenario: Duplicate tool name is rejected
- **GIVEN** a tool named `write_file` is registered
- **WHEN** another tool with name `write_file` is registered
- **THEN** ToolManager rejects the registration with a clear error

