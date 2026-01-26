## ADDED Requirements
### Requirement: Trusted tool listings for model prompts
`IToolProvider.list_tools()` SHALL derive tool definitions from the trusted capability registry exposed by `IToolGateway.list_capabilities()`; tool listings MUST NOT originate from untrusted sources (planner/model output).

#### Scenario: Tool provider uses the gateway registry
- **WHEN** the context assembles tool definitions for a model prompt
- **THEN** the tool provider queries the tool gateway capability registry and converts those capabilities into tool definitions for the prompt
