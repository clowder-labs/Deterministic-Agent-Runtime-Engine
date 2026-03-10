---
doc_kind: feature
topic_slug: retrospective-todo-hardening
topics: ["governance", "skills", "sop", "retrospective"]
created: 2026-03-09
updated: 2026-03-09
status: active
mode: todo_fallback
---

# Feature: retrospective-todo-hardening

## Scope
Harden the retrospective/process-governance path so explicitly deferred-but-required work is not lost in prose. This slice only changes the retrospective skill, the development-workflow handoff, and the SOP trigger/landing rules for routing deferred work into TODO artifacts.

## TODO Fallback Bundle
- Governance docs:
  - `docs/guides/Documentation_First_Development_SOP.md`
- Skills:
  - `.codex/skills/retrospective-process-hardening/SKILL.md`
  - `.codex/skills/development-workflow/SKILL.md`

## Governance Anchors
- `docs/guides/Development_Constraints.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `.codex/skills/development-workflow/SKILL.md`
- `.codex/skills/retrospective-process-hardening/SKILL.md`

## Evidence

### Commands
- `rm -f dare.log`
- `git diff --check`

### Results
- `rm -f dare.log`: removed the stray local test log so the docs-only branch stays clean and does not carry unrelated workspace noise.
- `git diff --check`: passed after updating the retrospective skill, development-workflow handoff, SOP wording, and this feature aggregation doc.

### Contract Delta
- `schema`: no runtime schema field changes are introduced in this docs-only slice because the governed surface is the retrospective workflow contract. The substantive contract change is that retrospective outputs now include a required deferred-follow-up classification path and a required deferred-writeback section for out-of-scope-but-required follow-ups.
- `error semantics`: no runtime `error_code` / `error_type` / `exception_class` / `ToolResult.error` payload contract changes are introduced because this slice does not touch execution-time error carriers. The governance delta is documentation-only and narrows how deferred work must be recorded after retrospective review.
- `retry`: no runtime retry protocol changes are introduced because this slice does not modify retry loops or delivery orchestration. Re-running the retrospective remains deterministic because deferred follow-ups must be written into tracked backlog artifacts instead of being left in prose-only summaries.

### Golden Cases
- `.codex/skills/retrospective-process-hardening/SKILL.md`
- `.codex/skills/development-workflow/SKILL.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `docs/features/retrospective-todo-hardening.md`

### Regression Summary
- Runner commands:
  - `git diff --check`
- Summary: pass 1, fail 0, skip 0.

### Observability and Failure Localization
- N/A for the runtime event chain in this docs-only governance slice because no execution path, transport path, or model/tool lifecycle was modified.
- Reason: there are no new runtime `start`, `tool_call`, `end`, or `fail` events to emit; the only affected surface is governance text and skill output requirements.
- Fallback evidence: `git diff --check`, the feature doc diff, and the PR review thread show whether the new retrospective contract is applied consistently.
- Runtime locator fields `run_id`, `tool_call_id`, `capability_id`, `attempt`, and `trace_id` are n.a. here because no runtime execution artifact is produced by this slice.
- Error locator semantics such as `error_code`, `error_type`, `exception_class`, and `ToolResult.error` are likewise n.a. because the change does not alter runtime error payloads; failure localization is instead anchored to the failing governance gate and review discussion.

### Structured Review Report
- Changed Module Boundaries / Public API: governance-only; no runtime public API changed.
- New State: retrospective output now has an explicit `todo-later` bucket, and workflow/SOP text requires those items to be written into TODO artifacts before closeout.
- Concurrency / Timeout / Retry: no runtime concurrency change.
- Side Effects and Idempotency: repeated retrospective runs should update the same TODO artifacts deterministically instead of spawning prose-only follow-ups.
- Coverage and Residual Risk: no automated gate yet enforces the new TODO-writeback behavior; enforcement currently relies on the skill/SOP contract.

### Behavior Verification
- Happy path: when a retrospective identifies out-of-scope-but-required work, the skill now classifies it as `todo-later` and requires a concrete TODO writeback target.
- Error/fallback path: the workflow no longer treats “mention it in the summary” as sufficient for deferred work; the SOP now requires TODO persistence in the same turn.

### Risks and Rollback
- Risk: until a dedicated gate exists, TODO writeback remains process-enforced rather than CI-enforced.
- Rollback: revert the three governance text updates and remove this feature aggregation doc if the repository decides to keep retrospective output prose-only.

### Review and Merge Gate Links
- Intent PR baseline: [#205](https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/205)
- Implementation PR: [#210](https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/210)
- Review thread: [review comment](https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/210#discussion_r2905515773)
