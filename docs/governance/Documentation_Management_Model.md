# Documentation Management Model

> Scope: Repository-wide documentation governance for design, analysis, feature lifecycle, standards, temporary notes, and archive.

## 1. Governance Targets

The documentation system MUST satisfy both goals:
- Reconstructability: system behavior can be rebuilt from docs.
- Traceability: any active change can be traced end-to-end in minutes.

### 1.1 Source-of-Truth Boundary

- `docs/**` is the canonical, full repository documentation source of truth.
- `openspec/**` is the change-execution process record (proposal/design/spec delta/tasks/evidence trace), not a replacement for canonical docs.
- Any OpenSpec execution outcome that affects long-term understanding MUST be written back into `docs/**` (especially design, feature aggregation, and TODO/analysis ledgers).
- Readers should be able to understand current architecture and behavior from `docs/**` without relying on OpenSpec internals beyond trace links.

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
3. Feature docs:
   - OpenSpec mode: place under `docs/features/<change-id>.md`
   - TODO fallback mode: place under `docs/features/<topic-slug>.md` with `mode: todo_fallback` + `topic_slug`
   - this aggregation doc remains the single source for feature/change status in either mode.
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
1. Perform full-scope analysis and maintain a master TODO backlog in `docs/todos/`.
2. Update canonical docs (`docs/design/**` and related governance docs) before execution.
3. Select one TODO slice and create/continue `openspec/changes/<change-id>/` for that slice.
4. Create/update `docs/features/<change-id>.md` and link proposal/design/specs/tasks.
5. Execute tasks iteratively; write evidence into feature aggregation + TODO ledger.
6. Verify with tests/checks; update docs consistency.
7. Archive the completed change and migrate feature doc to `docs/features/archive/`.
8. Repeat with next TODO slice until master TODO backlog is fully completed.

### 5.2 No-OpenSpec Fallback Mode (TODO-driven)

Use only when OpenSpec cannot be used (tooling/environment constraint):
1. Perform full-scope analysis and maintain a master TODO backlog in `docs/todos/`.
2. Update canonical docs (`docs/design/**` and related governance docs) before execution.
3. Create `docs/features/<topic-slug>.md` with `mode: todo_fallback` in frontmatter.
4. Execute against TODO checklist with evidence updates per task.
5. When OpenSpec becomes available, migrate fallback assets into one or more OpenSpec slice changes and link migration evidence.

### 5.3 OpenSpec Slicing Policy (Large Changes)

- OpenSpec change is an execution slice unit, not a full initiative container.
- A large feature/refactor/bug campaign SHOULD be split into multiple change-ids.
- Master TODO backlog in `docs/todos/` is the upstream planning input for slice creation.
- Each change MUST declare which TODO subset it consumes and must not claim unrelated TODO items.

## 6. Frontmatter Contract (Governance-tracked docs)

Governance-tracked docs MUST include frontmatter with:

```yaml
---
change_ids: ["<change-id>"]
doc_kind: feature|analysis|todo|standard|design|temporary
topics: ["..."]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft|active|done|archived
---
```

Recommended optional fields:
- `todo_ids`: list of master TODO item IDs covered by this document/change slice
- `mode`: `openspec` or `todo_fallback`
- `topic_slug`: required in fallback mode before `change_ids` is assigned

Notes:
- `status` on non-aggregation docs is informational only.
- Aggregation doc is the status source of truth.
- Explicit exceptions, if any, must be declared in the governing standard document for that doc family.
- TODO fallback mode exception: before OpenSpec change-id exists, fallback docs MUST provide `topic_slug` and `mode: todo_fallback`; `change_ids` becomes mandatory after migration into OpenSpec.

## 7. Checkpoint-to-Skill Mapping

Required lifecycle checkpoints MUST be skillized:
- kickoff
- execution-sync
- verification
- completion-archive

Skill contract (minimum two skills):
- management skill: `.codex/skills/documentation-management/SKILL.md`
- workflow skill: `.codex/skills/development-workflow/SKILL.md`

Checkpoint mapping:
- kickoff -> `development-workflow` (mode/scope) + `documentation-management` (baseline metadata/path)
- execution-sync -> `development-workflow` (evidence/status sync) + `documentation-management` (metadata consistency)
- verification -> `development-workflow` (gate/check commands + status conflict detection)
- completion-archive -> `development-workflow` (closure) + `documentation-management` (archive move and retention policy)

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
