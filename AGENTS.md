
# Additional Constraints

- When writing code, add necessary comments to clarify non-obvious logic or intent.
- When creating a commit, include a detailed commit message (summary + body with key changes and rationale).

## Documentation-First Governance (Mandatory)

- Agent-driven development MUST follow documents under `docs/guides/` first, especially:
  - `docs/guides/Development_Constraints.md`
  - `docs/guides/Documentation_First_Development_SOP.md`
- Documentation placement, lifecycle, and archive handling MUST follow:
  - `docs/governance/Documentation_Management_Model.md`
- Documentation governance tasks SHOULD use:
  - `.codex/skills/documentation-management/SKILL.md`
  - `.codex/skills/documentation-workflow/SKILL.md`
  - compatibility wrapper (legacy): `.codex/skills/documentation-lifecycle-governance/SKILL.md`
- Code implementation MUST align with `docs/design/` as the latest full design source of truth.
- If design and implementation diverge, update design docs first, then execute gap analysis before coding.
- Every design doc that governs implementation MUST explicitly contain:
  - overall architecture
  - core workflow
  - data structures
  - key interfaces
  - exception/error handling
- For any bug fix, feature, or refactor, follow the SOP sequence:
  1. update design docs
  2. generate design-code gap analysis
  3. derive TODO list from the analysis
  4. execute fixes via OpenSpec workflow task-by-task
  5. update TODO/evidence and archive analysis artifacts
