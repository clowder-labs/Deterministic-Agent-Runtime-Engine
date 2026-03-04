---
change_ids: ["enhance-doc-governance-traceability"]
doc_kind: feature
topics: ["documentation-governance", "traceability", "skills"]
created: 2026-02-28
updated: 2026-03-04
status: active
mode: openspec
---

# Feature: enhance-doc-governance-traceability

## Scope
Unify documentation management structure, lifecycle governance, and SOP-to-skill execution mapping.

## OpenSpec Artifacts
- Proposal: `openspec/changes/enhance-doc-governance-traceability/proposal.md`
- Design: `openspec/changes/enhance-doc-governance-traceability/design.md`
- Specs:
  - `openspec/changes/enhance-doc-governance-traceability/specs/documentation-lifecycle-traceability/spec.md`
  - `openspec/changes/enhance-doc-governance-traceability/specs/design-reconstructability-governance/spec.md`
- Tasks: `openspec/changes/enhance-doc-governance-traceability/tasks.md`

## Governance Anchors
- `docs/governance/Documentation_Management_Model.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `.codex/skills/documentation-management/SKILL.md`
- `.codex/skills/development-workflow/SKILL.md`

## Evidence

### Commands
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`
- `./scripts/ci/check_governance_traceability.sh`
- `./scripts/ci/check_governance_evidence_truth.sh`
- `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`

### Results
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`: passed (`53 passed`) after extending the traceability gate regression suite to cover governance standard/design/TODO frontmatter enforcement, active-feature `## TODO Coverage` checks in tasks artifacts, master TODO reverse mapping to concrete feature/tasks targets, stale active index entries, `Active Entries`-only membership checks, explicit checkpoint-to-skill pair rows, active/archive index path-family enforcement, README index-file exclusion for both active and archived entries, discrete `todo_ids` token matching, Claim Ledger-only TODO/change validation, same-record TODO/change validation, claim-scope range resolution, range-only claim-scope resolution without explicit todo tokens, full lifecycle checkpoint coverage, and date-prefixed archived change task discovery.
- `./scripts/ci/check_governance_traceability.sh`: passed against the real repository tree after tightening active/archive index membership to canonical sections, rejecting index entries outside the correct feature-doc path family, excluding `docs/features/README.md` and `docs/features/archive/README.md` from valid feature-entry targets, enforcing baseline frontmatter on governance standard/design docs plus concrete TODO ledgers, requiring explicit checkpoint-to-skill pair rows in Section 7, requiring active features with `todo_ids` to declare `## TODO Coverage` in their tasks artifact, and resolving Claim Ledger / slice-plan change targets back to concrete feature docs and tasks artifacts while skipping `planned` placeholder claims.
- `./scripts/ci/check_governance_evidence_truth.sh`: passed, confirming the new traceability assets do not break the existing evidence-first contract.
- `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).

### Contract Delta
- `schema`: added a canonical feature aggregation template, active/archive feature indexes, and a machine-checkable backlog-id pilot linkage for one active change.
- `error semantics`: no runtime API change; the new traceability gate fails structurally on missing template/index/mapping assets with deterministic file-scoped messages.
- `retry`: no retry semantic change; this slice is docs/CI only, and reruns remain deterministic after fixing the flagged governance asset.

### Golden Cases
- `docs/features/templates/feature_aggregation_template.md`
- `docs/features/README.md`
- `docs/features/archive/README.md`
- `docs/governance/Documentation_Management_Model.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `docs/todos/project_overall_todos.md`
- `docs/todos/agentscope_domain_execution_todos.md`
- `openspec/changes/agentscope-d2-d4-thinking-transport/tasks.md`
- `scripts/ci/check_governance_traceability.sh`
- `tests/unit/test_governance_traceability_gate.py`
- `docs/features/agentscope-d2-d4-thinking-transport.md`

### Regression Summary
- Runner commands:
  - `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`
  - `./scripts/ci/check_governance_traceability.sh`
  - `./scripts/ci/check_governance_evidence_truth.sh`
  - `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`
- Summary: pass 4, fail 0, skip 0.

### Observability and Failure Localization
- N/A for runtime event chain in this docs/CI governance slice.
- Reason: this slice only adds document topology and traceability checks; it does not modify runtime event emission.
- Fallback evidence: unit tests and both governance gate commands above exercise the failing/passing paths for template/index/mapping localization.

### Structured Review Report
- Changed Module Boundaries / Public API: governance scope only; no new runtime public API added.
- New State: expands the repository traceability gate, adds frontmatter to the baseline governance standard/design/TODO docs, and adds `## TODO Coverage` mapping to the pilot tasks artifact under `openspec/changes/agentscope-d2-d4-thinking-transport/`.
- Concurrency / Timeout / Retry: no concurrency change; gate runs are single-process document scans with deterministic rerun behavior after fixes.
- Side Effects and Idempotency: side effects are limited to CI/log output; repeated runs are idempotent against unchanged docs.
- Coverage and Residual Risk: template/index/skill-mapping/frontmatter/TODO-linkage/master-TODO-change-target checks are covered for the governance baseline docs and concrete TODO ledgers; residual risk is that broader standard/design families outside this baseline set are not yet auto-enforced.

### Behavior Verification
- Happy path: the repository now has a canonical feature aggregation template, explicit active/archive feature indexes, governance baseline docs with structured frontmatter, and a green traceability gate that resolves a pilot feature doc back to its TODO ledger, owning change-id, and tasks coverage through Claim Ledger records plus `## TODO Coverage` ranges such as `D2-1~D2-4, D4-1~D4-4`.
- Error/fallback path: the gate now fails deterministically when a governance standard/TODO doc drops frontmatter, when an active feature declares `todo_ids` but its tasks artifact omits `## TODO Coverage`, when a master TODO slice table points to a non-existent change target, when a feature doc is missing from `## Active Entries`, when an active/archive index entry points at the wrong doc family, when Section 7 keeps checkpoint names but drops the actual `checkpoint -> skill` mapping rows, or when `todo_ids` and `change_ids` only co-occur in detail-board/prose lines without a matching Claim Ledger record.

### Risks and Rollback
- Risk: frontmatter auto-enforcement is still scoped to the governance baseline standard/design docs and concrete TODO ledgers, not every standard/design file in the repository.
- Risk: `planned` Claim Ledger rows are intentionally excluded from reverse mapping checks until a concrete feature/tasks artifact exists, so future placeholder drift still depends on later activation checks.
- Risk: active/archive indexes are now explicit manual ledgers, so closeout changes that forget to update them will fail the new gate.
- Rollback: remove `governance-traceability` from `.github/workflows/ci-gate.yml` and revert the template/index additions if the new gate produces unexpected false positives.

### Review and Merge Gate Links
- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126`
- Baseline implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/137`
- Previous implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175`
- Current implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/178`
- Review request: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#issuecomment-3976690386`
- Key owner feedback: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#issuecomment-3976707233`
- Active fix threads:
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878449796`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878449803`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878551469`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878551474`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878634816`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878634820`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878773226`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878885299`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2881384029`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2881384034`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2881421738`

## Next Milestone
Complete `5.3` closeout: update TODO/archive records, archive `enhance-doc-governance-traceability`, and move the feature evidence into `docs/features/archive/`.
