## ADDED Requirements

### Requirement: Skill store builder composes loaders deterministically
The skill domain SHALL provide a `SkillStoreBuilder` that deterministically composes skill loaders and filtering rules before constructing an `ISkillStore`.

- `SkillStoreBuilder.config(config)` MUST derive filesystem skill loading roots from `Config.workspace_dir` and `Config.user_dir`.
- The builder MUST allow callers to append external skill loaders.
- The builder MUST support disabling skills by `skill_id` before final store exposure.
- The resulting `ISkillStore` MUST provide deterministic `list_skills()` and `get_skill(skill_id)` behavior after composition.

#### Scenario: Config-derived loader and external loader are combined
- **GIVEN** a `Config` with workspace and user directories
- **AND** an external loader is attached to `SkillStoreBuilder`
- **WHEN** `build()` is called
- **THEN** the resulting store contains skills from both config-derived filesystem loading and the external loader

#### Scenario: Disabled skill ids are filtered out
- **GIVEN** a composed skill store contains skill ids `a`, `b`, and `c`
- **AND** `disable_skill("b")` is configured
- **WHEN** `build()` is called
- **THEN** `list_skills()` excludes `b`
- **AND** `get_skill("b")` returns `None`
