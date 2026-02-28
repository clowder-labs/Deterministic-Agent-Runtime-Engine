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

4. Archive
- Move completed docs to `docs/features/archive/` after closeout.
