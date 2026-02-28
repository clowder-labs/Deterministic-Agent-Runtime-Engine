## 1. Governance contract and template baseline

- [ ] 1.0 Publish unified docs directory taxonomy and type-to-path mapping in governance model + docs navigation.
- [ ] 1.1 Define and publish the frontmatter field contract for governance-tracked documents (required vs optional fields).
- [ ] 1.2 Create a governance aggregation template keyed by OpenSpec change-id and add one example document.
- [ ] 1.3 Add an active governance index and archive index format with explicit migration rules.

## 2. Documentation alignment updates

- [ ] 2.1 Update `docs/guides/Documentation_First_Development_SOP.md` with aggregation/frontmatter/checkpoint execution order.
- [ ] 2.2 Update `docs/guides/Development_Constraints.md` to require governance aggregation entry + machine-checkable mapping.
- [ ] 2.3 Update `docs/design/Design_Reconstructability_Traceability_Matrix.md` to include links to governance aggregation entries.
- [ ] 2.4 Update standards to explicitly define OpenSpec default collaboration and TODO-driven fallback collaboration.

## 3. Automation and CI checkpoint implementation

- [ ] 3.1 Implement or extend CI checks to validate aggregation entry existence when governance-scoped files change.
- [ ] 3.2 Implement or extend CI checks to validate required frontmatter fields for governance-tracked docs.
- [ ] 3.3 Implement or extend CI checks to validate gap/TODO -> OpenSpec task mapping completeness.

## 4. SOP skillization implementation

- [ ] 4.1 Define and publish a checkpoint-to-skill mapping document for governance lifecycle stages.
- [ ] 4.2 Add or update at least two governance skills under repository-managed skills: `documentation-management` and `development-workflow`.
- [ ] 4.3 Add CI validation to ensure required governance checkpoint-skill mappings are present and non-stale.
- [ ] 4.4 Define reuse contract so `documentation-management` and `development-workflow` can be reused by both OpenSpec mode and TODO fallback mode.

## 5. Pilot backfill and closure evidence

- [ ] 5.1 Backfill one active governance change using the new aggregation + frontmatter + skill mapping contract as pilot evidence.
- [ ] 5.2 Run governance check scripts and capture passing command output in PR evidence.
- [ ] 5.3 Update TODO/archive records and mark this OpenSpec change as complete with evidence links.
