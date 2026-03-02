# Evidence Truth Implementation Strategy

> Scope: Governance changes that use `docs/features/*.md` as aggregation entry documents.
> Governing status scope: `active|in_review|in-review` (hyphen variant is normalized).

## 1. Goal

Evidence truth must be an auditable artifact, not a narrative promise.
For each active/in_review governance change, reviewers should be able to answer:
- what was executed,
- what passed/failed,
- what behavior was verified (happy path + error path),
- what risk remains and how rollback works,
- whether review/merge decisions are traceable.

## 2. Contract (Required Structure + Acceptance Pack)

Each active/in_review feature aggregation doc MUST include:
- `## Evidence`
- `### Commands`
- `### Results`
- `### Behavior Verification`
- `### Risks and Rollback`
- `### Review and Merge Gate Links`

`in_review` docs additionally MUST include:
- `### Contract Delta`
- `### Golden Cases`
- `### Regression Summary`
- `### Observability and Failure Localization`
- `### Structured Review Report`

`### Contract Delta` MUST declare these dimensions (changed or `none/n.a + reason`):
- schema impact,
- error semantics (`error_code`/`error_type`/`exception_class`/`ToolResult.error` mapping),
- retry semantics.

`### Golden Cases` MUST list newly added/updated golden files (file names are mandatory).

`### Regression Summary` MUST include:
- runner command list,
- pass/fail/skip summary.

`### Observability and Failure Localization` MUST include:
- event chain coverage: `start` / `tool_call` / `end` / `fail`,
- locator fields: `run_id`, `tool_call_id`, `capability_id`, `attempt`, `trace_id`,
- at least one error locator: `error_code` / `error_type` / `exception_class` / `ToolResult.error`.

Docs-only exception:
- if no runtime event chain exists, this section may be `N/A`, but must carry `reason/because` and fallback evidence pointer.

`### Structured Review Report` MUST answer:
- changed module boundaries / public API,
- new states (cache/global/singleton),
- new concurrency/timeout/retry and upper bounds,
- side effects and idempotency strategy,
- coverage scope and residual risk.

Frontmatter mode requirements:
- OpenSpec mode: `change_ids` required.
- TODO fallback mode: `mode: todo_fallback` + `topic_slug` required.

## 3. Implementation Strategy

### Phase 1 (now): Structural + semantic gate in CI

Use a deterministic script gate:
- script: `scripts/ci/check_governance_evidence_truth.sh`
- checks:
  - baseline evidence headings exist in active/in_review feature aggregation docs (with tolerant heading variants)
  - acceptance-pack headings are hard-required for `in_review` docs
  - acceptance-pack semantic markers exist in required sections
  - frontmatter keys satisfy mode contract
  - OpenSpec artifact paths listed in aggregation docs are repository-resolvable files
  - review/merge gate section contains both intent/implementation PR links and at least one review link
  - intent/implementation links must reference distinct PR numbers
  - zero governed docs in scope is a hard failure (prevents draft/skip bypass)
  - intent-before-implementation ordering signal is warning-only in this phase

This phase blocks structurally incomplete and semantically unreviewable records.

### Phase 2: Consistency checks

Add semantic assertions:
- command/result pairing is present for each listed command
- behavior verification includes both happy path and changed error branch
- unresolved risk items are explicit (or marked none with reason)
- review thread fix records reference concrete commits
- acceptance-pack items are cross-consistent with changed contracts and regression outputs

### Phase 3: Merge policy coupling

Connect evidence truth with merge policy:
- merge gate requires evidence section completeness for active/in_review governance change docs
- fallback-mode changes require explicit migration-debt note before closeout
- archive transition requires evidence links to remain resolvable
- reviewer default path is evidence-first; deep code reading is risk-triggered sampling

## 4. Operational Rules

- Evidence truth is owned by the current change implementer.
- Reviewers validate acceptance-pack links and semantic completeness before approval.
- `docs/mailbox/` entries tagged as `audit_evidence` are retained (not deleted by default).
- Any temporary downgrade from blocking to warning must be documented in the feature doc risk section.
- If acceptance pack is missing required items, review outcome MUST be `request changes`.

## 5. Command of Record

Primary gate command:

```bash
./scripts/ci/check_governance_evidence_truth.sh
```

This command is intended to run both locally and in CI.
