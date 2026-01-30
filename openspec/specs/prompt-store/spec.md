# prompt-store Specification

## Purpose
TBD - created by archiving change add-component-manager-entrypoints. Update Purpose after archive.
## Requirements
### Requirement: Prompt store interface
The system SHALL define an `IPromptStore` interface that retrieves Prompts by `prompt_id` with optional model identity and optional version metadata.

The interface MUST provide a deterministic lookup API (e.g., `get(prompt_id, model=None, version=None)`) and MUST return either the resolved Prompt or a not-found error.

When a model identity is provided, the prompt store MUST select the Prompt whose `supported_models` includes the model identity or `*`, preferring the highest `order` value. If multiple candidates share the same `order`, the store MUST break ties deterministically using source precedence (workspace > user > built-in) and then stable source order.

If a version is provided, the store MUST only consider Prompts with a matching `version`.

#### Scenario: Prompt retrieval for a model
- **GIVEN** a prompt store contains multiple `base.system` Prompts
- **AND** at least one definition supports model identity `openai`
- **WHEN** a component requests `base.system` with model identity `openai`
- **THEN** the `IPromptStore` returns the highest `order` matching Prompt or a not-found error

### Requirement: Prompt schema
Prompts MUST include:
- `prompt_id`
- `role`
- `content`
- `supported_models`
- `order`
- optional `version`

`supported_models` MUST accept a wildcard value `*` that matches any model identity, and `order` MUST be an integer priority where higher values are preferred.

Prompts MAY include optional `name` and `metadata` fields that are preserved when converting to runtime messages.

#### Scenario: Wildcard Prompt
- **GIVEN** a Prompt with `supported_models` containing `*`
- **WHEN** the store resolves a prompt for any model identity
- **THEN** the wildcard Prompt is eligible for selection

### Requirement: Prompt loader interface
The system SHALL define an `IPromptLoader` interface that loads Prompts from a single source.

Loaders MUST return Prompts in a stable order to support deterministic tie-breaking when multiple entries share the same `order`.

#### Scenario: Loader preserves manifest order
- **GIVEN** a prompt manifest lists prompts in a specific order
- **WHEN** a loader reads the manifest
- **THEN** the returned Prompts preserve the manifest order

### Requirement: Default layered prompt store sources
The system SHALL provide a default `IPromptStore` implementation that can load Prompts from:
- built-in prompt manifests shipped with the framework
- user-level prompt overrides under `<user_dir>/<prompt_store_path_pattern>`
- workspace-level prompt overrides under `<workspace_dir>/<prompt_store_path_pattern>`

The config value `prompt_store_path_pattern` MUST default to `.dare/_prompts.json`.

Prompt retrieval MUST be deterministic and apply override precedence: workspace > user > built-in.

#### Scenario: Workspace overrides built-in
- **GIVEN** `base.system` exists in built-in prompts
- **AND** a workspace prompt manifest exists at `<workspace_dir>/.dare/_prompts.json`
- **WHEN** the prompt store retrieves `base.system`
- **THEN** it returns the workspace prompt content

### Requirement: Default prompt store factory
The model domain SHALL provide a public factory function for constructing the default prompt store, and cross-domain callers MUST use that factory instead of importing `_internal` prompt store implementations directly.

#### Scenario: Builder constructs default prompt store
- **GIVEN** a builder that needs the default prompt store
- **WHEN** it constructs the store
- **THEN** it calls the model domain prompt store factory and does not import `_internal` implementations

