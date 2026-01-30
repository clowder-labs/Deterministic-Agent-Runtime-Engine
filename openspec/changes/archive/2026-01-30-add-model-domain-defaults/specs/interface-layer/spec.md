## ADDED Requirements
### Requirement: Default model adapter manager fallback
When no explicit model adapter and no model adapter manager are provided, builders SHALL fall back to a default model adapter manager created by the model domain factory and resolve the adapter using the effective `Config`.

#### Scenario: Builder uses default manager
- **GIVEN** a builder with no explicit model adapter
- **AND** no model adapter manager is provided
- **WHEN** `build()` is called
- **THEN** the builder uses the model domain default manager to resolve the adapter using `Config.llm`
