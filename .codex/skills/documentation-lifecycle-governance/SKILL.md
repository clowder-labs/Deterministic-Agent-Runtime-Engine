---
name: documentation-lifecycle-governance
description: Use when existing workflows reference a legacy single-entry documentation governance skill and you need a compatibility wrapper for management and workflow skills.
---

# Documentation Lifecycle Governance

## Purpose
This is a compatibility wrapper to preserve old references.

Use these two primary skills directly for new work:
- `documentation-management`
- `documentation-workflow`

## Delegation contract

1. Run `documentation-management` for:
- document classification and placement
- frontmatter and metadata checks
- archive path and retention policy enforcement

2. Run `documentation-workflow` for:
- mode selection (OpenSpec default, TODO fallback)
- lifecycle checkpoints (`kickoff`, `execution-sync`, `verification`, `completion-archive`)
- evidence and status synchronization

3. Compatibility guarantee:
- any workflow still invoking `documentation-lifecycle-governance` must execute the two skills above in this order:
  1) `documentation-management`
  2) `documentation-workflow`
