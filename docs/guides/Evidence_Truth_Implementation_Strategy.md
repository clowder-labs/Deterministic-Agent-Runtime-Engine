# Evidence Truth Implementation Strategy

> Scope: Governance changes that use `docs/features/*.md` as aggregation entry documents.

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
- `### Contract Delta`
- `### Golden Cases`
- `### Regression Summary`
- `### Observability and Failure Localization`
- `### Structured Review Report`
- `### Behavior Verification`
- `### Risks and Rollback`
- `### Review and Merge Gate Links`

`### Contract Delta` MUST describe:
- schema changes,
- error code changes,
- retry semantic changes.

`### Golden Cases` MUST list newly added/updated golden files (file names are mandatory).

`### Regression Summary` MUST include:
- runner command list,
- pass/fail/skip summary.

`### Observability and Failure Localization` MUST include:
- event chain coverage: `start` / `tool_call` / `end` / `fail`,
- locator fields: `run_id`, `tool_call_id`, `capability_id`, `attempt`, `error_code`, `trace_id`.

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
  - required evidence headings exist in active/in_review feature aggregation docs
  - acceptance-pack semantic markers exist in required sections
  - frontmatter keys satisfy mode contract
  - OpenSpec artifact paths listed in aggregation docs are repository-resolvable files
  - review/merge gate section contains both intent/implementation PR links and at least one review link

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
