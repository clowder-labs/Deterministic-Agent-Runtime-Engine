## Summary
- What does this PR change?
- Why is this change needed?

## Scope (One PR One Thing)
- Primary objective:
- Out of scope:
- I confirm this PR handles a single objective only: [ ] Yes

## Changed Files (required)
List all touched files and why each file changed.

| File | Reason |
| --- | --- |
| path/to/file | reason |

If this PR is a large diff (>300 changed lines), explain why split PRs are not possible and provide a split follow-up plan.

## Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2

## Test Evidence (required)
- Local commands run:
  - `...`
- CI links or job names:
  - `...`
- Evidence/output summary:
  - `...`

If this PR changes high-risk runtime paths (auth/concurrency/execution control), include `risk-matrix` evidence.

## Risk and Rollback
- Risk level: Low / Medium / High
- Main risk points:
- Rollback plan:

## Dependency and Lockfile Changes
- Lockfile changed in this PR: [ ] Yes [ ] No
- If yes, manifest updated in same PR (`requirements.txt`/`pyproject.toml`/`package.json`): [ ] Yes [ ] No [ ] N/A

## Agent Rules Checklist (required)
Reference: `docs/agent_rules.md`

- [ ] Only task-related files changed; no opportunistic refactor
- [ ] Public interfaces/data structures unchanged unless explicitly required
- [ ] Tests added/updated and evidence attached
- [ ] Any `skip/only/exclude` usage is explained and reviewed
- [ ] Merge will be done by approved reviewer (no self-merge auto-ship)
