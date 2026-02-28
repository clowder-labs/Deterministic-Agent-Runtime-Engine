---
name: documentation-workflow
description: Use when executing documentation governance work to run lifecycle checkpoints, OpenSpec-default collaboration, TODO fallback, and evidence sync.
---

# Documentation Workflow

## When to use
Use this skill when documentation work must follow lifecycle checkpoints from kickoff to archive.

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
- confirm change/topic scope and collaboration mode
- create or refresh feature aggregation doc
- run `documentation-management` to validate type/path/frontmatter baseline

2. execution-sync
- keep OpenSpec tasks, TODO status, and feature aggregation evidence aligned
- update linked design/gap/TODO docs per completed task

3. verification
- run required checks (`openspec validate`, `openspec status`, and repo doc checks)
- verify status consistency: feature doc is source of truth, linked docs are non-conflicting

4. completion-archive
- mark work done in feature aggregation and related ledgers
- run `documentation-management` archive actions
- ensure archived entries stay discoverable via index/evidence links

## Output expectations
For each workflow run, report:
- mode used (`openspec` or `todo_fallback`)
- checkpoint completion (`kickoff`, `execution-sync`, `verification`, `completion-archive`)
- evidence commands executed
- unresolved risks or migration debt
