# Acceptance Pack Spec

> Scope: Implementation pull requests in this repository.
> Goal: Make review evidence machine-checkable and reviewer-friendly.

## 1. Mandatory Items

Each implementation PR MUST provide all items below in `docs/features/<change-id>.md` under `## Evidence`:

1. `### Contract Delta`
2. `### Golden Cases`
3. `### Regression Summary`
4. `### Observability and Failure Localization`
5. `### Structured Review Report`

If any item is missing, the PR is non-compliant.

Gate scope and status normalization:
- gate scope is `status: active|in_review|in-review` (hyphen form normalized to underscore form).
- strict acceptance-pack enforcement is applied to `in_review` docs.
- `active` docs are required to keep baseline evidence structure (`Evidence/Commands/Results/Behavior/Risks/Review links`) and review links.
- if no governed feature doc is found in scope, the gate fails.

## 2. Item Contract

### 2.1 Contract Delta

Must declare all three dimensions (changed or `none/n.a + reason`):
- schema impact
- error semantics (`error_code`/`error_type`/`exception_class`/`ToolResult.error`)
- retry semantics

### 2.2 Golden Cases

Must list new/updated golden file names.
If no golden change is needed, write explicit `none` with reason.

### 2.3 Regression Summary

Must include:
- runner commands
- pass/fail/skip summary

### 2.4 Observability and Failure Localization

Default requirement (runtime-affecting changes): must cover chain markers:
- start
- tool_call
- end
- fail

Default requirement (runtime-affecting changes): must include locator fields:
- run_id
- tool_call_id
- capability_id
- attempt
- trace_id

Default requirement (runtime-affecting changes): must include at least one error locator:
- error_code
- error_type
- exception_class
- ToolResult.error

Docs-only exception:
- If no runtime chain exists, `Observability` may be `N/A`, but MUST include:
  - explicit reason (`reason`/`because`),
  - fallback evidence pointer (for example regression commands/results section).

### 2.5 Structured Review Report

Must answer all topics:
- Changed Module Boundaries / Public API
- New State
- Concurrency / Timeout / Retry
- Side Effects and Idempotency
- Coverage and Residual Risk

## 3. Intent / Implementation Link

Review links MUST include:
- intent PR link
- implementation PR link
- at least one review comment/review thread link

And MUST satisfy:
- intent PR and implementation PR must reference different PR numbers.
- intent merged before implementation is currently a soft check (warning).

## 4. Gate Command

Primary gate command:

```bash
./scripts/ci/check_governance_evidence_truth.sh
```

The gate is expected to run locally and in CI.
