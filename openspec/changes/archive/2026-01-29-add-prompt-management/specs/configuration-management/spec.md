## ADDED Requirements
### Requirement: Prompt configuration fields
The Config model SHALL include optional top-level fields used by prompt management:
- `prompt_store_path_pattern`
- `default_prompt_id`

`prompt_store_path_pattern` MUST be a string path pattern used by the default prompt store to locate prompt manifests.
`default_prompt_id` MAY be omitted or null; when set, it identifies the prompt_id used as the default system prompt.

#### Scenario: Prompt config values are exposed
- **GIVEN** prompt configuration values are set in config layers
- **WHEN** the effective Config is produced
- **THEN** it exposes `prompt_store_path_pattern` and `default_prompt_id` for prompt resolution
