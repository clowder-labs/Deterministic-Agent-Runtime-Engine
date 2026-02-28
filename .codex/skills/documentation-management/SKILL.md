---
name: documentation-management
description: Use when classifying, creating, relocating, or archiving repository documents to enforce taxonomy, directory placement, and governance metadata contracts.
---

# Documentation Management

## When to use
Use this skill for documentation structure operations:
- create a new governance-tracked document
- move/rename documentation by type
- add or update frontmatter metadata
- archive completed documentation records

This skill supersedes `documentation-lifecycle-governance` for documentation governance management responsibilities.

## Core responsibilities

1. Classify document kind
- `standard`, `design`, `feature`, `analysis`, `todo`, `temporary`

2. Enforce type-to-path mapping
- `standard` -> `docs/guides/` or top-level governance rule docs
- `design` -> `docs/design/`
- `feature` -> `docs/features/`
- `analysis` / `todo` -> `docs/todos/`
- `temporary` -> `docs/mailbox/` with mailbox class:
  - `temporary_coordination`: short-lived thread notes, removable after cleanup
  - `audit_evidence`: review/approval/decision evidence, retained and archived
- archived assets -> `docs/features/archive/`, `docs/todos/archive/`, `docs/design/archive/`

3. Enforce governance metadata
- ensure frontmatter exists for governance-tracked docs
- required keys (OpenSpec mode): `change_ids`, `doc_kind`, `topics`, `created`, `updated`, `status`
- required keys (TODO fallback mode): `topic_slug`, `mode: todo_fallback`, `doc_kind`, `topics`, `created`, `updated`, `status`
- required keys for mailbox docs: `owner_thread`, `cleanup_plan`, `mailbox_class`
- when fallback assets are migrated into OpenSpec, add `change_ids` and retain `topic_slug` as historical linkage when useful

4. Enforce archive policy
- completed feature entries move to `docs/features/archive/`
- completed TODO/analysis entries move to `docs/todos/archive/` or be marked archived in index
- `temporary_coordination` mailbox docs may be removed only after cleanup completion is recorded
- `audit_evidence` mailbox docs MUST NOT be deleted; they must remain linked from feature evidence and archived as historical record
- do not delete historical evidence unless explicitly approved

5. Maintain lifecycle dependency definition
- ensure documentation dependencies are explicit and consistent:
  - `standards -> design update -> gap analysis -> master TODO -> feature aggregation -> execution evidence -> review/merge gate -> archive`

6. Maintain planning-to-execution mapping
- ensure master TODO ledger exists before execution slicing
- for each OpenSpec change, record covered TODO subset (`todo_ids` or equivalent linkage)
- prevent one change from claiming unrelated TODO scope
- ensure review threads and merge-gate decisions are linked from feature evidence

7. Keep CI gate scope complete (not skill-only)
- enforce that CI checks include metadata, link resolution, evidence completeness, and TODO/change trace mapping
- treat skill-file existence/mapping as one gate dimension, not the full governance gate

## Output expectations
For each management action, provide:
- affected files
- old path -> new path mapping (if moved)
- metadata fields changed
- archive/lifecycle status change
