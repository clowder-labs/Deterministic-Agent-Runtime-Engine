---
change_ids: ["enhance-doc-governance-traceability"]
doc_kind: feature
topics: ["documentation-governance", "traceability", "skills"]
created: 2026-02-28
updated: 2026-03-02
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
- `./scripts/ci/check_governance_evidence_truth.sh`
- `openspec validate --changes enhance-doc-governance-traceability`
- `openspec status --change enhance-doc-governance-traceability --json`

### Results
- `check_governance_evidence_truth.sh`: pass.
- `openspec validate`: pass.
- `openspec status`: pass, `isComplete: true`.

### Contract Delta
- `schema`: evidence contract now requires a full acceptance-pack layout in every active feature doc (`Contract Delta`, `Golden Cases`, `Regression Summary`, `Observability and Failure Localization`, `Structured Review Report`).
- `error_code`: no runtime API `error_code` schema change; governance gate failures now surface deterministic missing-section signals that block merge.
- `retry`: CI retry does not bypass policy checks; rerun only after evidence/doc fixes, with no semantic downgrade on retry.

### Golden Cases
- Updated evidence contract baseline: `docs/guides/Evidence_Truth_Implementation_Strategy.md`.
- Added acceptance-pack canonical spec: `docs/governance/Acceptance_Pack_Spec.md`.
- Updated PR authoring baseline: `.github/pull_request_template.md`.

### Regression Summary
- Runner commands:
  - `./scripts/ci/check_governance_evidence_truth.sh`
  - `openspec validate --changes enhance-doc-governance-traceability`
  - `openspec status --change enhance-doc-governance-traceability --json`
- Summary: pass 3, fail 0, skip 0.

### Observability and Failure Localization
- Event chain coverage includes `start`, `tool_call`, `end`, and `fail` events for traceable execution lifecycle.
- Failure localization fields required for triage and review are: `run_id`, `tool_call_id`, `capability_id`, `attempt`, `error_code`, `trace_id`.
- Gate failures must emit enough context to locate the exact document/section mismatch without full code deep-dive.

### Structured Review Report
- Changed Module Boundaries / Public API: governance scope only; no new runtime public API added.
- New State: no new cache/global/singleton runtime state; only documentation governance state tightened.
- Concurrency / Timeout / Retry: no new concurrent runtime path; retry policy is documentation gate rerun after fixes, with unchanged timeout semantics.
- Side Effects and Idempotency: side effects are limited to docs/CI gate outputs; idempotency relies on deterministic section checks and repeatable command outputs.
- Coverage and Residual Risk: governance evidence and OpenSpec validation are covered; residual risk is false positives from regex-based checks when section names drift from canonical wording.

### Behavior Verification
- Happy path: governance flow remains `analysis -> master TODO -> OpenSpec slice execution` with docs as canonical source.
- Error/fallback path: TODO fallback metadata now requires `mode: todo_fallback` + `topic_slug`, with explicit migration back to OpenSpec.

### Risks and Rollback
- Risk: CI checks not yet fully implemented as scripts may leave policy drift windows.
- Rollback: keep contract wording changes, temporarily downgrade new CI gate checks to warning if false positives block delivery.

### Review and Merge Gate Links
- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126`
- Implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/137`
- Review request: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#issuecomment-3976690386`
- Key owner feedback: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#issuecomment-3976707233`
- Active fix threads:
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#discussion_r2867257929`
  - `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126#discussion_r2867257932`

## Next Milestone
Implement tasks group 1-2 (taxonomy contract + standards alignment).
