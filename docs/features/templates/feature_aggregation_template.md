# Feature Aggregation Template

Use this template for new `docs/features/<change-id>.md` entries in OpenSpec mode.

```yaml
---
change_ids: ["<change-id>"]
doc_kind: feature
topics: ["topic-a", "topic-b"]
todo_ids: ["OPTIONAL-TODO-ID"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
mode: openspec
---
```

```md
# Feature: <change-id>

## Scope
Describe the slice boundary and the user-visible or contract-visible outcome.

## OpenSpec Artifacts
- Proposal: `openspec/changes/<change-id>/proposal.md`
- Design: `openspec/changes/<change-id>/design.md`
- Specs:
  - `openspec/changes/<change-id>/specs/<spec-name>/spec.md`
- Tasks: `openspec/changes/<change-id>/tasks.md`

## Governance Anchors
- `docs/guides/Development_Constraints.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- Add the canonical design or governance docs changed by this slice.

## Evidence

### Commands
- `exact command`

### Results
- `pass/fail + key summary`

### Behavior Verification
- Happy path:
- Error/fallback path:

### Risks and Rollback
- Risk:
- Rollback:

### Review and Merge Gate Links
- Intent PR:
- Implementation PR:
- Review thread:
```
