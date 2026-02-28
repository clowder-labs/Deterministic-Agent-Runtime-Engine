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
- bind work to `openspec/changes/<change-id>/`
- maintain `docs/features/<change-id>.md` as the single status source

2. TODO fallback mode (only if OpenSpec unavailable)
- create `docs/features/<topic-slug>.md` with `mode: todo_fallback`
- create dated gap/TODO pair in `docs/todos/`
- once OpenSpec is available, migrate fallback assets into an OpenSpec change

## Lifecycle checkpoints

1. kickoff
- classify request as `bug` / `feature` / `refactor`
- choose collaboration mode (OpenSpec default, TODO fallback only when OpenSpec unavailable)
- update `docs/design/**` first (no implementation before design update)
- create/update gap analysis and TODO ledger before implementation
- create or refresh feature aggregation doc as the status source
- run `documentation-management` to validate type/path/frontmatter baseline

2. execution-sync
- execute in small increments: TODO item -> OpenSpec task -> implementation -> evidence
- keep OpenSpec tasks, TODO status, and feature aggregation evidence aligned
- after each completed task, update linked design/gap/TODO docs and implementation evidence

3. verification
- run required checks (`openspec validate`, `openspec status`, tests, and repo doc checks)
- verify coverage of interface contracts and error branches for changed behavior
- verify status consistency: feature doc is source of truth, linked docs are non-conflicting

4. completion-archive
- mark work done in feature aggregation and related ledgers
- run `documentation-management` archive actions
- update TODO/archive indexes (for example `docs/todos/README.md` when applicable)
- complete OpenSpec archive when the change is finished
- ensure archived entries stay discoverable via index/evidence links

## Output expectations
For each workflow run, report:
- mode used (`openspec` or `todo_fallback`)
- checkpoint completion (`kickoff`, `execution-sync`, `verification`, `completion-archive`)
- evidence commands executed
- evidence file updates (design, TODO, OpenSpec tasks, feature aggregation)
- unresolved risks or migration debt
