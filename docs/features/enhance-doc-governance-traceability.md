---
change_ids: ["enhance-doc-governance-traceability"]
doc_kind: feature
topics: ["documentation-governance", "traceability", "skills"]
created: 2026-02-28
updated: 2026-03-03
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
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`: passed (`44 passed`) after extending the traceability gate regression suite to also cover stale active index entries, `Active Entries`-only membership checks, discrete `todo_ids` token matching, same-record TODO/change validation, claim-scope range resolution, full lifecycle checkpoint coverage, and date-prefixed archived change task discovery.
- `./scripts/ci/check_governance_traceability.sh`: passed against the real repository tree after tightening active/archive index membership to canonical sections and resolving pilot `todo_ids` through either direct ledger rows or same-claim scope ranges.
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
- New State: adds one new repository gate script, one new gate test file, and canonical docs/index/template assets under `docs/features/`.
- Concurrency / Timeout / Retry: no concurrency change; gate runs are single-process document scans with deterministic rerun behavior after fixes.
- Side Effects and Idempotency: side effects are limited to CI/log output; repeated runs are idempotent against unchanged docs.
- Coverage and Residual Risk: template/index/skill-mapping/TODO-linkage checks are covered; residual risk is that broader frontmatter enforcement across `docs/guides/**` and `docs/design/**` is still pending.

### Behavior Verification
- Happy path: the repository now has a canonical feature aggregation template, explicit active/archive feature indexes, and a green traceability gate that resolves a pilot feature doc back to its TODO ledger and owning change-id, including claim-ledger scope ranges such as `D2-1~D2-4, D4-1~D4-4`.
- Error/fallback path: the new gate fails deterministically when a feature doc is missing from the `## Active Entries` section, when the template/archive index is missing, when checkpoint-skill mapping drifts, or when declared `todo_ids` and `change_ids` only co-occur in different ledger records.

### Risks and Rollback
- Risk: `3.2-3.4` are still open, so the new gate does not yet enforce full frontmatter coverage for every governance-tracked doc family or full master-TODO/task completeness.
- Risk: active/archive indexes are now explicit manual ledgers, so closeout changes that forget to update them will fail the new gate.
- Rollback: remove `governance-traceability` from `.github/workflows/ci-gate.yml` and revert the template/index additions if the new gate produces unexpected false positives.

### Review and Merge Gate Links
- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126`
- Implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/137`
- Current implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175`
- Review request: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#issuecomment-3976690386`
- Key owner feedback: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#issuecomment-3976707233`
- Active fix threads:
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878449796`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878449803`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878551469`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878551474`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878634816`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878634820`

## Next Milestone
Implement the remaining CI depth tasks: widen frontmatter enforcement beyond feature docs and add machine-checkable TODO/task and master-TODO/change-slice consistency checks before closeout.
