---
change_ids: ["enhance-doc-governance-traceability"]
doc_kind: feature
topics: ["documentation-governance", "traceability", "skills"]
created: 2026-02-28
updated: 2026-03-04
status: done
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
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`: passed (`53 passed`) after extending the traceability gate regression suite to cover archived-feature frontmatter validation, TODO Claim (`active/done`) -> OpenSpec `tasks.md` completeness checks, and project master TODO `Detail Claim Ref` consistency against execution-board claims.
- `./scripts/ci/check_governance_traceability.sh`: passed against the real repository tree after extending the gate to validate frontmatter contract on both active and archived feature aggregation docs, enforce Claim Ledger-to-OpenSpec task artifact mapping for executable claims, and enforce master TODO/detail-board claim reference consistency checks.
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
- New State: extends the existing governance traceability gate and regression suite with closeout checks for frontmatter scope, claim-to-task mapping, and master/detail claim consistency.
- Concurrency / Timeout / Retry: no concurrency change; gate runs are single-process document scans with deterministic rerun behavior after fixes.
- Side Effects and Idempotency: side effects are limited to CI/log output; repeated runs are idempotent against unchanged docs.
- Coverage and Residual Risk: template/index/skill-mapping/TODO-linkage plus closeout-depth checks (`3.2-3.4`) are covered; residual risk is future expansion of frontmatter strictness from feature docs to additional governance doc families.

### Behavior Verification
- Happy path: the repository now has a canonical feature aggregation template, explicit active/archive feature indexes, and a green traceability gate that resolves a pilot feature doc back to its TODO ledger and owning change-id through Claim Ledger records, including scope ranges such as `D2-1~D2-4, D4-1~D4-4`, even when the concrete TODO id does not appear elsewhere in the file.
- Error/fallback path: the new gate fails deterministically when a feature doc is missing from the `## Active Entries` section, when an active/archive index entry points at the wrong doc family, when Section 7 keeps checkpoint names but drops the actual `checkpoint -> skill` mapping rows, or when `todo_ids` and `change_ids` only co-occur in detail-board/prose lines without a matching Claim Ledger record.

### Risks and Rollback
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
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878773226`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2878885299`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2881384029`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2881384034`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/175#discussion_r2881421738`

## Next Milestone
Promote `p0-gate` to branch protection required check and then archive this change entry in the next closeout pass.
