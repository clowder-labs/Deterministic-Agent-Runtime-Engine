## 1. Governance contract and template baseline

- [x] 1.0 Publish unified docs directory taxonomy and type-to-path mapping in governance model + docs navigation.
  Evidence: `docs/governance/Documentation_Management_Model.md` and `docs/README.md` define the docs directory taxonomy and governance navigation contract.
- [x] 1.1 Define and publish the frontmatter field contract for governance-tracked documents (required vs optional fields).
  Evidence: `docs/governance/Documentation_Management_Model.md` Section 6 defines the frontmatter contract by mode.
- [x] 1.2 Create a governance aggregation template keyed by OpenSpec change-id and add one example document.
  Evidence: `docs/features/templates/feature_aggregation_template.md` plus active feature docs under `docs/features/`.
- [x] 1.3 Add an active governance index and archive index format with explicit migration rules.
  Evidence: `docs/features/README.md` and `docs/features/archive/README.md`.

## 2. Documentation alignment updates

- [x] 2.1 Update `docs/guides/Documentation_First_Development_SOP.md` with aggregation/frontmatter/checkpoint execution order.
  Evidence: `docs/guides/Documentation_First_Development_SOP.md` Sections 1, 2, 7, and 8.
- [x] 2.2 Update `docs/guides/Development_Constraints.md` to require governance aggregation entry + machine-checkable mapping.
  Evidence: `docs/guides/Development_Constraints.md` hard-gate bullets under 文档先行硬门禁.
- [x] 2.3 Update `docs/design/Design_Reconstructability_Traceability_Matrix.md` to include links to governance aggregation entries.
  Evidence: `docs/design/Design_Reconstructability_Traceability_Matrix.md` Governance 聚合锚点 table.
- [x] 2.4 Update standards to explicitly define OpenSpec default collaboration and TODO-driven fallback collaboration.
  Evidence: `docs/guides/Documentation_First_Development_SOP.md` Section 7 and `docs/governance/Documentation_Management_Model.md` Section 5.
- [x] 2.5 Update standards to explicitly define `docs/**` as canonical full record and `openspec/**` as execution trace record.
  Evidence: `docs/guides/Documentation_First_Development_SOP.md` Section 1 and `docs/governance/Documentation_Management_Model.md` Section 1.1.
- [x] 2.6 Define analysis-first + master-TODO-first workflow and multi-change OpenSpec slicing policy.
  Evidence: `docs/guides/Documentation_First_Development_SOP.md`, `docs/todos/README.md`, and `docs/governance/Documentation_Management_Model.md`.

## 3. Automation and CI checkpoint implementation

- [x] 3.1 Implement or extend CI checks to validate aggregation entry existence when governance-scoped files change.
  Evidence: `scripts/ci/check_governance_traceability.sh`, `tests/unit/test_governance_traceability_gate.py`, and `.github/workflows/ci-gate.yml`.
- [ ] 3.2 Implement or extend CI checks to validate required frontmatter fields for governance-tracked docs.
- [ ] 3.3 Implement or extend CI checks to validate gap/TODO -> OpenSpec task mapping completeness.
- [ ] 3.4 Implement or extend CI checks to validate master TODO -> OpenSpec change-slice mapping consistency.
- [x] 3.5 Implement evidence truth structural gate (`scripts/ci/check_governance_evidence_truth.sh`) and wire it into `ci-gate`.
  Evidence: `scripts/ci/check_governance_evidence_truth.sh`, `tests/unit/test_governance_evidence_truth_gate.py`, and `.github/workflows/ci-gate.yml`.

## 4. SOP skillization implementation

- [x] 4.1 Define and publish a checkpoint-to-skill mapping document for governance lifecycle stages.
  Evidence: `docs/governance/Documentation_Management_Model.md` Section 7 and `docs/guides/Documentation_First_Development_SOP.md` Section 8.
- [x] 4.2 Add or update at least two governance skills under repository-managed skills: `documentation-management` and `development-workflow`.
  Evidence: `.codex/skills/documentation-management/SKILL.md` and `.codex/skills/development-workflow/SKILL.md`.
- [x] 4.3 Add CI validation to ensure required governance checkpoint-skill mappings are present and non-stale.
  Evidence: `scripts/ci/check_governance_traceability.sh` validates the mapping section and required skill paths.
- [x] 4.4 Define reuse contract so `documentation-management` and `development-workflow` can be reused by both OpenSpec mode and TODO fallback mode.
  Evidence: `docs/governance/Documentation_Management_Model.md`, `docs/guides/Documentation_First_Development_SOP.md`, and `.codex/skills/development-workflow/SKILL.md`.

## 5. Pilot backfill and closure evidence

- [x] 5.1 Backfill one active governance change using the new aggregation + frontmatter + skill mapping contract as pilot evidence.
  Evidence: `docs/features/agentscope-d2-d4-thinking-transport.md` now declares `todo_ids` that resolve back to `docs/todos/agentscope_domain_execution_todos.md`.
- [x] 5.2 Run governance check scripts and capture passing command output in PR evidence.
- [ ] 5.3 Update TODO/archive records and mark this OpenSpec change as complete with evidence links.
