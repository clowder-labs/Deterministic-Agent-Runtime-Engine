## ADDED Requirements
### Requirement: Prompt store interface
The system SHALL define an `IPromptStore` interface that retrieves prompt templates by name and optional version metadata.

#### Scenario: Prompt retrieval
- **WHEN** a component requests a prompt by name and version
- **THEN** the `IPromptStore` MUST return the matching prompt template or a not-found error
