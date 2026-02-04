# Skill Domain Assessment

> Status: draft (2026-02-03). Scope: `dare_framework/skill` only.

## 1. Scope & Responsibilities

- Parse/load Agent Skills (SKILL.md + scripts/).
- Store and select skills for a task.
- Expose skill prompts via `search_skill` tool.
- Provide optional prompt enrichment with skill content.

## 2. Current Public Surface (Facade)

`dare_framework.skill` exports:
- Types: `Skill`
- Interfaces: `ISkill` (non-executable), `ISkillTool`, `ISkillLoader`, `ISkillStore`, `ISkillSelector`

Supported defaults live under `dare_framework.skill.defaults`.

## 3. Actual Dependencies

- Tool domain: `ISkillTool` extends `ITool`; `SkillSearchTool` returns prompt text via `ToolResult`.
- Agent builder: loads skills via `FileSystemSkillLoader` at build time.
- Context: uses prompt enricher to inject skill content into system prompt.

## 3.1 Skill Modes

- `skill_mode = "agent"`: single agent mounts `initial_skill_path` (multi-skill orchestration TBD).
- `skill_mode = "search_tool"`: single agent registers `search_skill` tool.

## 4. Findings (Gaps / Overexposure / Mismatches)

1. **Overexposed defaults (mitigated)**
   - Defaults are moved under `skill.defaults` to keep the facade minimal.

2. **Stable boundary clarity**
   - Kernel/interfaces split is required to separate stable contracts vs defaults.
   - `ISkillTool` is a marker interface with no extra behavior; used by `SkillSearchTool`.

3. **Prompt enrichment alignment**
   - `prompt_enricher` should use `Skill.to_context_section()` for consistent prompt output.

4. **Frontmatter parsing is intentionally minimal**
   - `_skill_parser` only supports flat `key: value` strings.
   - Only `name`/`description` are consumed; extra keys are ignored.

5. **Skill search policy surface is thin**
   - No config gating or allowlist for which skills can be returned.
   - Mode switching (skill-as-agent vs search_tool) is partial; multi-skill agent mode is TBD.

## 5. Minimal Public Surface (Proposed)

- **Keep in `dare_framework.skill`**:
  - `Skill` (data model)
  - `ISkill`, `ISkillTool`, `ISkillLoader`, `ISkillStore`, `ISkillSelector`

- **Move defaults to explicit namespace**:
  - `FileSystemSkillLoader`, `SkillStore`, `KeywordSkillSelector`, `SkillSearchTool`
  - Suggested module: `dare_framework.skill.defaults`

- **Keep internal-only**:
  - `_skill_parser`, `prompt_enricher`, `NoOpSkill`

## 6. Doc Updates Needed

- `doc/design/modules/skill/README.md`: clarify stable surface vs defaults; align prompt injection behavior.
- `doc/design/Framework_MinSurface_Review.md`: ensure the “Keep/Hide” list matches the new public surface.

## 7. Proposed Implementation Plan (Skill Domain)

1. **Kernel split**: move `ISkill`/`ISkillTool` into `skill/kernel.py` and keep loaders/selectors in `skill/interfaces.py`.
2. **Defaults namespace**: move default implementations to `skill/defaults.py` (or a small `defaults/` package); update imports.
3. **Skill modes**: add `skill_mode` + `skill_paths` config for `search_tool` mode; multi-skill agent mode TBD.
4. **Prompt enrichment alignment**: reuse `Skill.to_context_section()` for injected prompts.
5. **Frontmatter parsing**: keep flat key/value format; only consume `name`/`description`.
6. **Policy hooks**: add config gating for skill search if required.
7. **Update examples/tests/docs** accordingly.

## 8. Implementation Note

- `search_skill` tool results are mounted into Context (current skill) so they are included by `context.assemble`.
