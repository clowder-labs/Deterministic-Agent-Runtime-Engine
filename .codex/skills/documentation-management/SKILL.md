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

## Core responsibilities

1. Classify document kind
- `standard`, `design`, `feature`, `analysis`, `todo`, `temporary`

2. Enforce type-to-path mapping
- `standard` -> `docs/guides/` or top-level governance rule docs
- `design` -> `docs/design/`
- `feature` -> `docs/features/`
- `analysis` / `todo` -> `docs/todos/`
- `temporary` -> `docs/mailbox/`
- archived assets -> `docs/features/archive/`, `docs/todos/archive/`, `docs/design/archive/`

3. Enforce governance metadata
- ensure frontmatter exists for governance-tracked docs
- required keys: `change_ids`, `doc_kind`, `topics`, `created`, `updated`, `status`

4. Enforce archive policy
- completed feature entries move to `docs/features/archive/`
- completed TODO/analysis entries move to `docs/todos/archive/` or be marked archived in index
- do not delete historical evidence unless explicitly approved

## Output expectations
For each management action, provide:
- affected files
- old path -> new path mapping (if moved)
- metadata fields changed
- archive/lifecycle status change
