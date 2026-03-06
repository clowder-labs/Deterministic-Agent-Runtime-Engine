# Feature Aggregation Docs

`docs/features/` stores one aggregation document per active change/topic.

## Rules

1. File naming
- OpenSpec mode: `docs/features/<change-id>.md`
- TODO fallback mode: `docs/features/<topic-slug>.md`

2. Source of truth
- Aggregation document owns lifecycle status (`draft/active/done/archived`).
- Linked analysis/todo/design docs should not override this status.

3. Required links
- OpenSpec artifacts (`proposal/design/specs/tasks`) or TODO fallback bundle
- Related design docs
- Gap analysis + TODO evidence
- Verification evidence (commands/results)

4. Required evidence truth structure
- `## Evidence`
- `### Commands`
- `### Results`
- `### Behavior Verification`
- `### Risks and Rollback`
- `### Review and Merge Gate Links`
- CI gate command: `./scripts/ci/check_governance_traceability.sh`
- CI gate command: `./scripts/ci/check_governance_evidence_truth.sh`

5. Archive
- Move completed docs to `docs/features/archive/` after closeout.

## Template

- Canonical template: `docs/features/templates/feature_aggregation_template.md`

## Active Entries

- `docs/features/add-anthropic-model-adapter.md`
- `docs/features/agentscope-d2-d4-thinking-transport.md`
- `docs/features/agentscope-d5-safe-compression.md`
- `docs/features/agentscope-d7-plan-state-tools.md`
- `docs/features/enhance-doc-governance-traceability.md`
- `docs/features/client-session-resume.md`
- `docs/features/p0-conformance-gate.md`
- `docs/features/p0-default-eventlog.md`
- `docs/features/p0-step-driven-execution.md`

## Archive Index

- `docs/features/archive/README.md`

## Migration Rules

- Active feature docs live in `docs/features/` until completion-archive.
- Closeout must update this active index and the archive index in the same change.
- Archived feature docs move to `docs/features/archive/` and keep stable evidence links.
