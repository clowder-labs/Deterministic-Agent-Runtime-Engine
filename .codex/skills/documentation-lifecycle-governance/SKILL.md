---
name: documentation-lifecycle-governance
description: Use when creating, updating, relocating, or archiving repository docs to enforce taxonomy, lifecycle, and OpenSpec/TODO collaboration rules.
---

# Documentation Lifecycle Governance

## When to use
Use this skill when any documentation asset is created or modified.

## Core workflow

1. Classify the document type:
- design / analysis / todo / feature / standard / temporary

2. Place in the correct directory:
- design -> `docs/design/`
- analysis/todo -> `docs/todos/`
- feature aggregation -> `docs/features/`
- standard -> `docs/guides/` or governance rule files
- temporary -> `docs/mailbox/`

3. Link lifecycle dependencies:
- standards -> feature -> design -> analysis -> TODO -> execution -> evidence -> archive

4. Choose collaboration mode:
- OpenSpec mode (default): bind doc to `openspec/changes/<change-id>/`
- TODO fallback mode: use dated TODO bundle and add migration plan to OpenSpec

5. Enforce governance metadata:
- add/update frontmatter for governance-tracked docs
- ensure aggregation document is the single status source

6. Verify before completion:
- run documentation checks (OpenSpec status/validate + repo doc checks)
- ensure links and evidence paths are resolvable

7. Archive policy:
- move completed feature docs to `docs/features/archive/`
- move completed TODO bundles to `docs/todos/archive/`
- never delete historical evidence without explicit governance approval

## Output expectations
For each doc governance task, produce:
- affected files list
- lifecycle status transition
- evidence commands executed
- remaining open questions/risk
