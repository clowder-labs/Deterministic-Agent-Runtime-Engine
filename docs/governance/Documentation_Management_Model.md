# Documentation Management Model

> Scope: Repository-wide documentation governance for design, analysis, feature lifecycle, standards, temporary notes, and archive.

## 1. Governance Targets

The documentation system MUST satisfy both goals:
- Reconstructability: system behavior can be rebuilt from docs.
- Traceability: any active change can be traced end-to-end in minutes.

## 2. Directory Taxonomy (Single Source)

| Layer | Path | Purpose | Lifecycle |
|---|---|---|---|
| Standards | `docs/guides/`, `docs/agent_rules.md`, `AGENTS.md` | Rules, constraints, SOP, collaboration protocol | stable + versioned |
| Design | `docs/design/` | Authoritative architecture/interface/module design | active + archived |
| Governance | `docs/governance/` | Governance model, branch rules, policy checkpoints | stable |
| Feature Aggregation | `docs/features/` | One aggregation doc per change/topic (single status source) | active -> archive |
| Analysis/TODO | `docs/todos/` | Gap analysis and execution TODO ledgers | active -> archive |
| Temporary | `docs/mailbox/` | Thread-local or short-lived communication artifacts | temporary -> archive/remove |
| Reference | `docs/appendix/` | Supporting references and non-normative materials | stable |
| Archives | `docs/design/archive/`, `docs/todos/archive/`, `docs/features/archive/` | Historical snapshots and closed records | immutable-ish |

## 3. Document Types and Placement Rules

1. Design docs: place under `docs/design/**`; must align with current implementation contract.
2. Analysis docs: place under `docs/todos/` as dated gap analysis and TODO pairs.
3. Feature docs: place under `docs/features/<change-id>.md`; this is the single source for feature/change status.
4. Standards docs: place under `docs/guides/` or top-level governance rule files.
5. Temporary docs: place under `docs/mailbox/`; must be linked to an owner thread and cleanup plan.

## 4. Lifecycle Dependencies

The default dependency chain is:

`standards -> feature aggregation -> design update -> gap analysis -> TODO -> execution -> evidence -> archive`

Status transitions:
- `draft` -> `active` -> `done` -> `archived`
- only aggregation docs own lifecycle state; linked docs SHOULD NOT duplicate conflicting status values.

## 5. Collaboration Modes

### 5.1 OpenSpec Mode (Default)

Use this whenever OpenSpec is available:
1. Create/continue `openspec/changes/<change-id>/`.
2. Create/update `docs/features/<change-id>.md` and link proposal/design/specs/tasks.
3. Execute tasks iteratively; write evidence into feature aggregation + TODO ledger.
4. Verify with tests/checks; update docs consistency.
5. Archive change and migrate feature doc to `docs/features/archive/` when complete.

### 5.2 No-OpenSpec Fallback Mode (TODO-driven)

Use only when OpenSpec cannot be used (tooling/environment constraint):
1. Create `docs/features/<topic-slug>.md` with `mode: todo_fallback` in frontmatter.
2. Create dated gap/TODO pair in `docs/todos/`.
3. Execute against TODO checklist with evidence updates per task.
4. When OpenSpec becomes available, migrate fallback assets into an OpenSpec change and link migration evidence.

## 6. Frontmatter Contract (Governance-tracked docs)

Governance-tracked docs SHOULD include frontmatter with:

```yaml
---
change_ids: ["<change-id>"]
doc_kind: feature|analysis|todo|standard|temporary
topics: ["..."]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft|active|done|archived
---
```

Notes:
- `status` on non-aggregation docs is informational only.
- Aggregation doc is the status source of truth.

## 7. Checkpoint-to-Skill Mapping

Required lifecycle checkpoints MUST be skillized:
- kickoff
- execution-sync
- verification
- completion-archive

Skill contract (minimum two skills):
- management skill: `.codex/skills/documentation-management/SKILL.md`
- workflow skill: `.codex/skills/documentation-workflow/SKILL.md`
- compatibility wrapper (legacy): `.codex/skills/documentation-lifecycle-governance/SKILL.md`

Checkpoint mapping:
- kickoff -> `documentation-workflow` (mode/scope) + `documentation-management` (baseline metadata/path)
- execution-sync -> `documentation-workflow` (evidence/status sync) + `documentation-management` (metadata consistency)
- verification -> `documentation-workflow` (gate/check commands + status conflict detection)
- completion-archive -> `documentation-workflow` (closure) + `documentation-management` (archive move and retention policy)

CI MUST validate:
- required skill files exist,
- checkpoint mapping is declared,
- required assets and linkages are present.

## 8. Effectiveness Criteria

Governance is considered effective when:
- active change context can be located in <= 5 minutes,
- traceability mapping completeness >= 95%,
- stale/unlinked governance docs trend down each iteration,
- archive migration occurs within one iteration after completion.
