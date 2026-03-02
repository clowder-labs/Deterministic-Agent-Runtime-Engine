---
name: development-workflow
description: Use when executing change delivery work to run OpenSpec-default workflow checkpoints, TODO fallback, and evidence synchronization.
---

# Development Workflow

## When to use
Use this skill for any `bug` / `feature` / `refactor` delivery that must follow the repository documentation-first SOP.
Invoke it before implementation starts and when closing the change lifecycle.

Do not use this skill for document-only relocation/classification tasks; use `documentation-management` directly for those.

**REQUIRED SUB-SKILL:** `documentation-management` for classification, placement, metadata, and archive moves.

## Collaboration mode selection

1. OpenSpec mode (default)
- build from docs-first inputs: analysis + master TODO + updated design docs
- bind one TODO slice to `openspec/changes/<change-id>/`
- maintain `docs/features/<change-id>.md` as the single status source for that slice
- treat OpenSpec artifacts as execution records; keep canonical outcomes written in `docs/**`

2. TODO fallback mode (only if OpenSpec unavailable)
- still start from analysis + master TODO + updated design docs
- create `docs/features/<topic-slug>.md` with `mode: todo_fallback` and required `topic_slug` frontmatter
- create dated gap/TODO pair in `docs/todos/`
- once OpenSpec is available, migrate fallback assets into one or more OpenSpec slice changes

## Required evidence block in feature aggregation doc

Each active/in_review feature aggregation doc MUST contain an `## Evidence` section with at least:
- commands executed (exact commands)
- command results (pass/fail + key output summary)
- contract delta (`schema`/`error_code`/`retry`)
- golden case file updates
- regression summary (runner output)
- observability/failure localization (`start/tool_call/end/fail` + locator fields)
- structured review report (module boundary/state/concurrency/side-effect/coverage)
- behavior verification (happy path + changed error branch)
- risks and rollback notes
- review/merge-gate evidence links (review request, key review threads, merge gate result)

Reference contract: `docs/guides/Evidence_Truth_Implementation_Strategy.md`.

## Lifecycle checkpoints

1. kickoff
- classify request as `bug` / `feature` / `refactor`
- choose collaboration mode (OpenSpec default, TODO fallback only when OpenSpec unavailable)
- complete global analysis before execution
- build/update a master TODO backlog that covers the full scope
- declare ownership in the target TODO ledger before implementation (`Claim ID`, `TODO scope`, `owner`, `expires`, `change-id`)
- update `docs/design/**` first (no implementation before design update)
- create or refresh feature aggregation doc as the status source
- initialize/refresh the required evidence block in feature aggregation doc before execution
- for OpenSpec mode, select one TODO slice as current change scope
- decide whether the slice needs an execution board (`multiple owners`, `shared contracts`, `Gate freeze`, or `touch-scope collision`)
- create or refresh the docs-only intent PR payload before any implementation begins
- require the docs-only intent PR to merge into `main` before coding
- run `documentation-management` to validate type/path/frontmatter baseline

2. execution-sync
- begin only after the docs-only intent PR is merged
- OpenSpec mode: execute in small increments `TODO slice item -> OpenSpec task -> implementation -> evidence`
- TODO fallback mode: execute in small increments `TODO item -> implementation -> evidence`, and record pending OpenSpec migration mapping
- keep master TODO status and feature aggregation evidence aligned in all modes
- keep claim ledger, execution board, and feature/OpenSpec slice aligned when ownership or scope changes
- after each completed task, update linked design/gap/TODO docs and implementation evidence
- append command outputs and behavior-check results to the feature evidence block at task granularity
- for large initiatives, continue by opening the next TODO slice in a new OpenSpec change instead of overloading one change

3. verification
- OpenSpec mode checks: `openspec validate`, `openspec status`, tests, and repo doc checks
- TODO fallback mode checks: tests, repo doc checks, TODO ledger completeness, and migration debt note completeness
- verify current OpenSpec slice only claims TODO items actually completed in this slice
- verify the intent PR was merged before the first implementation commit for the slice
- verify claim ownership is consistent between TODO ledger and any execution board
- verify coverage of interface contracts and error branches for changed behavior
- verify status consistency: feature doc is source of truth, linked docs are non-conflicting
- verify `docs/**` can stand alone as the current-state record without depending on OpenSpec internals
- verify governance CI scope is complete (frontmatter by mode, link resolution, evidence block completeness, TODO->change mapping, checkpoint mapping)
- verify feature evidence block includes acceptance-pack semantics and structured review report content
- verify review links include both intent PR and implementation PR records

4. review-merge-gate
- request review with explicit evidence links from the feature aggregation doc
- reviewer default path is evidence-first, then risk-targeted code sampling (contract boundary + control-flow/side-effects)
- process review feedback thread-by-thread and keep evidence section updated with fix commits
- require explicit non-blocking merge gate signal (approval or equivalent repo policy signal) before archive
- keep mailbox records linked: temporary coordination notes vs retained audit evidence

5. completion-archive
- mark work done in feature aggregation and related ledgers
- run `documentation-management` archive actions
- update TODO/archive indexes (for example `docs/todos/README.md` when applicable)
- OpenSpec mode: complete OpenSpec archive when the change is finished
- TODO fallback mode: archive fallback docs/ledgers and keep an explicit migration plan/status until OpenSpec migration is completed
- if master TODO still has pending slices, keep initiative active and start next slice workflow
- ensure archived entries stay discoverable via index/evidence links

## Output expectations
For each workflow run, report:
- mode used (`openspec` or `todo_fallback`)
- checkpoint completion (`kickoff`, `execution-sync`, `verification`, `review-merge-gate`, `completion-archive`)
- evidence commands executed
- evidence results summary (including changed happy path + error branch checks)
- evidence file updates (design, TODO, OpenSpec tasks, feature aggregation)
- claim updates and intent-PR status
- review and merge-gate status
- unresolved risks or migration debt
