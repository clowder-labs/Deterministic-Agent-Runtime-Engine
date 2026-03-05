---
change_ids: ["enhance-doc-governance-traceability"]
doc_kind: feature
topics: ["documentation-governance", "traceability", "skills", "intent-merge-gate"]
created: 2026-02-28
updated: 2026-03-05
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
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_intent_gate.py tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`
- `./scripts/ci/check_governance_traceability.sh`
- `./scripts/ci/check_governance_evidence_truth.sh`
- `GOVERNANCE_INTENT_GATE_CHANGED_FILES=$'client/main.py\ndocs/features/enhance-doc-governance-traceability.md' GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE='zts212653/Deterministic-Agent-Runtime-Engine#126=merged' ./scripts/ci/check_governance_intent_gate.sh`
- `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`

### Results
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_intent_gate.py tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`: passed (`56 passed`) after adding intent-gate regression coverage for docs-only skip behavior, implementation-path gating, governed feature-doc requirement, intent PR link extraction, merged-state enforcement, and draft-status exclusion while preserving existing traceability/evidence truth coverage.
- `./scripts/ci/check_governance_traceability.sh`: passed against the real repository tree after tightening active/archive index membership to canonical sections, rejecting index entries outside the correct feature-doc path family, excluding `docs/features/README.md` and `docs/features/archive/README.md` from valid feature-entry targets, requiring explicit checkpoint-to-skill pair rows in Section 7, and resolving pilot `todo_ids` only through Claim Ledger records, including same-claim scope ranges where the TODO id is only implied by the claim range.
- `./scripts/ci/check_governance_evidence_truth.sh`: passed, confirming the new traceability assets do not break the existing evidence-first contract.
- `GOVERNANCE_INTENT_GATE_CHANGED_FILES=$'client/main.py\ndocs/features/enhance-doc-governance-traceability.md' GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE='zts212653/Deterministic-Agent-Runtime-Engine#126=merged' ./scripts/ci/check_governance_intent_gate.sh`: passed, confirming implementation-path changes are now hard-blocked unless governed feature docs carry a merged `Intent PR`.
- `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).

### Contract Delta
- `schema`: added a dedicated intent gate script plus CI job wiring and governance guide updates that formalize implementation-path gate semantics.
- `error semantics`: no runtime API change; intent gate failures are deterministic and file-scoped (`missing governed feature doc`, `missing Intent PR link`, `Intent PR not merged`).
- `retry`: no retry semantic change; reruns are deterministic after fixing docs linkage or merged-state prerequisites.

### Golden Cases
- `docs/features/templates/feature_aggregation_template.md`
- `docs/features/README.md`
- `docs/features/archive/README.md`
- `scripts/ci/check_governance_traceability.sh`
- `scripts/ci/check_governance_intent_gate.sh`
- `tests/unit/test_governance_traceability_gate.py`
- `tests/unit/test_governance_intent_gate.py`
- `docs/features/agentscope-d2-d4-thinking-transport.md`

### Regression Summary
- Runner commands:
  - `../../.venv/bin/python -m pytest -q tests/unit/test_governance_intent_gate.py tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`
  - `./scripts/ci/check_governance_traceability.sh`
  - `./scripts/ci/check_governance_evidence_truth.sh`
  - `GOVERNANCE_INTENT_GATE_CHANGED_FILES=$'client/main.py\ndocs/features/enhance-doc-governance-traceability.md' GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE='zts212653/Deterministic-Agent-Runtime-Engine#126=merged' ./scripts/ci/check_governance_intent_gate.sh`
  - `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`
- Summary: pass 5, fail 0, skip 0.

### Observability and Failure Localization
- N/A for runtime event chain in this docs/CI governance slice.
- Reason: this slice only adds document topology and traceability checks; it does not modify runtime event emission.
- Fallback evidence: unit tests and both governance gate commands above exercise the failing/passing paths for template/index/mapping localization.

### Structured Review Report
- Changed Module Boundaries / Public API: governance scope only; no new runtime public API added.
- New State: adds intent gate policy state (`implementation-path diff -> governed feature doc -> merged intent PR`) with one new gate script and one new regression test suite.
- Concurrency / Timeout / Retry: no concurrency change; gate runs are single-process document scans with deterministic rerun behavior after fixes.
- Side Effects and Idempotency: side effects are limited to CI/log output; repeated runs are idempotent against unchanged docs.
- Coverage and Residual Risk: intent-merge gating plus existing template/index/skill-mapping/TODO-linkage checks are covered; residual risk is that broader frontmatter enforcement across `docs/guides/**` and `docs/design/**` is still pending.

### Behavior Verification
- Happy path: when implementation files change, CI now requires a same-PR governed feature-doc update and validates that the referenced `Intent PR` is already merged before allowing merge.
- Error/fallback path: the intent gate fails deterministically when implementation changes omit governed feature docs, when feature docs miss `Intent PR` links, or when the referenced intent PR state is not `merged`.

### Risks and Rollback
- Risk: `3.2-3.4` are still open, so the governance suite still does not enforce full frontmatter coverage for every governance-tracked doc family or full master-TODO/task completeness.
- Risk: active/archive indexes are now explicit manual ledgers, so closeout changes that forget to update them will fail the new gate.
- Risk: local runs without `GITHUB_TOKEN` need PR-state fixture or CI context for merged-state lookup.
- Rollback: remove `governance-intent-gate` from `.github/workflows/ci-gate.yml` and revert `scripts/ci/check_governance_intent_gate.sh` if false positives block delivery.

### Review and Merge Gate Links
- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126`
- Implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/137`
- Current implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/189`
- Follow-up implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/197`
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
Implement the remaining CI depth tasks: widen frontmatter enforcement beyond feature docs and add machine-checkable TODO/task and master-TODO/change-slice consistency checks before closeout.
