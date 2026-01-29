## ADDED Requirements
### Requirement: Model identity for prompt resolution
The system SHALL use the model adapter's stable identity (`IModelAdapter.name`) when resolving prompts by `supported_models`.

#### Scenario: Model identity is used for resolution
- **GIVEN** a model adapter named `openai`
- **WHEN** the runtime resolves prompts for that adapter
- **THEN** the model identity used for matching is `openai`

### Requirement: Prompt selection precedence and overrides
The system SHALL resolve the base system prompt using the following precedence:
1) Explicit Prompt override provided by the builder
2) Explicit `prompt_id` override provided by the builder
3) Config `default_prompt_id`
4) Model-aware prompt selection from the prompt store

If both a Prompt and a `prompt_id` override are set, the last builder call MUST replace the previous override so only one override is active.

#### Scenario: Explicit Prompt overrides prompt store selection
- **GIVEN** a builder sets an explicit Prompt override
- **WHEN** the agent is initialized
- **THEN** the resolved base system prompt uses the explicit Prompt content

#### Scenario: Prompt id overrides default prompt id
- **GIVEN** `default_prompt_id` is configured
- **AND** the builder sets a `prompt_id` override
- **WHEN** the agent is initialized
- **THEN** the resolved base system prompt uses the override `prompt_id`

### Requirement: Agent initialization loads prompt information
Agents SHALL resolve the prompt information needed for context assembly during initialization using the selected model adapter, the configured prompt store, and any prompt overrides/default prompt id.

#### Scenario: Agent initialization binds base system prompt
- **WHEN** an agent is built with a model adapter
- **THEN** the agent can assemble prompts that include the resolved base system prompt before user/assistant turn messages
