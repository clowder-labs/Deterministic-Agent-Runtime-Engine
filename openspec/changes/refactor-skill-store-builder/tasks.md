## 1. Skill loading model unification
- [x] 1.1 Add `SkillStoreBuilder` to compose config-derived filesystem loader + external loaders.
- [x] 1.2 Extend filesystem skill loader to resolve default roots from `Config.workspace_dir` and `Config.user_dir`.
- [x] 1.3 Add disabled-skill filtering in the store/build pipeline.

## 2. Builder/context skill-mode behavior
- [x] 2.1 Refactor agent builder to use `_enable_skill_tool` as the only skill-mode toggle.
- [x] 2.2 When `_enable_skill_tool=true`, auto-register `search_skill` and ignore `sys_skill` in default assemble path.
- [x] 2.3 When `_enable_skill_tool=false`, skip `search_skill` auto-registration and preserve explicit `sys_skill` behavior.
- [x] 2.4 Keep `assemble_context` externally injectable and compatible with the new skill-loading cache.

## 3. Tooling and config cleanup
- [x] 3.1 Collapse duplicated skill-search tool behavior to one canonical `SearchSkillTool` implementation.
- [x] 3.2 Remove `Config` fields `initial_skill_path`, `skill_mode`, and `skill_paths` from parsing and serialization.
- [x] 3.3 Update dependent call sites (e.g., A2A agent card skill loading) to the new config-derived path strategy.

## 4. Tests and validation
- [x] 4.1 Add unit tests for `SkillStoreBuilder` composition and disabled-skill filtering.
- [x] 4.2 Add/adjust builder tests for `_enable_skill_tool` true/false behavior.
- [x] 4.3 Run `openspec validate refactor-skill-store-builder --strict`.
- [ ] 4.4 Run targeted pytest for modified modules. (Blocked: pre-existing `@runtime_checkable` misuse on `infra.IComponent` causes test collection failure)
