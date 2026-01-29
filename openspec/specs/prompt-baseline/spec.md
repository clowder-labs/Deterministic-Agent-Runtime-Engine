# prompt-baseline Specification

## Purpose
TBD - created by archiving change add-basic-chat-flow. Update Purpose after archive.
## Requirements
### Requirement: Base system prompt via prompt store
The system SHALL provide a default English base system prompt through the default `IPromptStore` implementation under a stable name (e.g., `base.system`) and expose it to context assembly.

When a model adapter is available, the runtime MUST resolve the base system prompt using the prompt store's model-aware selection semantics (match `supported_models`, prefer highest `order`, fallback to `*`).

The built-in `base.system` prompt MUST include `supported_models: ["*"]` with the lowest `order` among base system prompts.

#### Scenario: Default prompt retrieval
- **WHEN** the runtime requests the base system prompt without specifying a version
- **THEN** the prompt store returns the default English system prompt content

#### Scenario: Model-aware prompt selection
- **GIVEN** the active model adapter name is `openai`
- **AND** the prompt store contains multiple `base.system` Prompts
- **AND** at least one Prompt supports `openai` with a higher `order` than the wildcard prompt
- **WHEN** the runtime assembles context for a model request
- **THEN** the resolved base system prompt content comes from the highest `order` Prompt that supports `openai`

#### Scenario: Context assembly uses the base prompt
- **WHEN** an assembled context is built for a milestone
- **THEN** the first message in the assembled context is the resolved base system prompt

