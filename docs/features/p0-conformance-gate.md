---
change_ids: ["p0-conformance-gate"]
doc_kind: feature
topics: ["p0", "conformance", "ci-gate", "runtime-validation"]
created: 2026-03-03
updated: 2026-03-03
status: active
mode: openspec
---

# Feature: p0-conformance-gate

## Scope

将 P0 运行时不变量收敛成统一的 `p0-gate` 质量门禁，覆盖安全门控、`step_driven` 执行闭环、默认事件链审计三类关键约束，并把 CI / 发布流程接入这条硬门槛。

## OpenSpec Artifacts

- Proposal: `openspec/changes/p0-conformance-gate/proposal.md`
- Design: `openspec/changes/p0-conformance-gate/design.md`
- Specs:
  - `openspec/changes/p0-conformance-gate/specs/p0-conformance-gate/spec.md`
  - `openspec/changes/p0-conformance-gate/specs/validation/spec.md`
  - `openspec/changes/p0-conformance-gate/specs/core-runtime/spec.md`
- Tasks: `openspec/changes/p0-conformance-gate/tasks.md`

## Governance Anchors

- `docs/guides/Development_Constraints.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `openspec/specs/core-runtime/spec.md`
- `openspec/specs/validation/spec.md`

## Evidence

### Commands

- `git fetch origin`
- `git worktree add .worktrees/p0-conformance-gate -b codex/p0-conformance-gate origin/main`
- `../../.venv/bin/python -m pytest -q tests/unit/test_transport_adapters.py tests/unit/test_interaction_dispatcher.py tests/unit/test_transport_channel.py tests/integration/test_client_cli_flow.py tests/unit/test_examples_cli.py tests/unit/test_examples_cli_mcp.py`
- `../../.venv/bin/python -m pytest -q tests/integration/test_security_policy_gate_flow.py`
- `../../.venv/bin/python -m pytest -q tests/integration/test_p0_conformance_gate.py`
- `../../.venv/bin/python -m pytest -q tests/integration/test_security_policy_gate_flow.py tests/integration/test_p0_conformance_gate.py tests/unit/test_dare_agent_step_driven_mode.py`
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_security_policy_gate.py tests/unit/test_dare_agent_security_boundary.py tests/unit/test_five_layer_agent.py`
- `../../.venv/bin/python -m pytest -q tests/unit/test_p0_gate_ci.py`
- `../../.venv/bin/python scripts/ci/p0_gate.py`
- `openspec validate p0-conformance-gate --type change --strict --json --no-interactive`
- `./scripts/ci/check_governance_evidence_truth.sh`

### Results

- `git fetch origin`: confirmed `origin/main` advanced to merge commit `36c8b38`, which includes the completed archive closeout for `refactor-dare-agent-structure-split` and provides the clean baseline for the next active change.
- `git worktree add .worktrees/p0-conformance-gate -b codex/p0-conformance-gate origin/main`: created an isolated continuation workspace for the next active change directly from merged `main`.
- `../../.venv/bin/python -m pytest -q tests/unit/test_transport_adapters.py tests/unit/test_interaction_dispatcher.py tests/unit/test_transport_channel.py tests/integration/test_client_cli_flow.py tests/unit/test_examples_cli.py tests/unit/test_examples_cli_mcp.py`: passed (`76 passed, 1 warning`) as the current baseline for the already-landed P0-related contract coverage recorded under tasks `2.4` and `5.1`.
- `../../.venv/bin/python -m pytest -q tests/integration/test_security_policy_gate_flow.py`: passed (`3 passed, 1 warning`) after extending the integration file to cover the full security gate decision surface: direct allow, direct deny with structured `not_allow`, and approval-required escalation.
- `../../.venv/bin/python -m pytest -q tests/integration/test_p0_conformance_gate.py`: passed (`2 passed, 1 warning`) after adding the missing step-driven integration anchor that exercises the full `agent("task")` closed loop, covering both ordered happy-path execution and fail-fast behavior when the first validated step fails.
- `../../.venv/bin/python -m pytest -q tests/integration/test_security_policy_gate_flow.py tests/integration/test_p0_conformance_gate.py tests/unit/test_dare_agent_step_driven_mode.py`: passed (`28 passed, 1 warning`) after the new `p0` integration file also absorbed the default event-log replay/hash-chain runtime anchor, confirming the security gate slice, step-driven closed-loop slice, and audit-chain slice can run together as the emerging P0 gate bundle.
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_security_policy_gate.py tests/unit/test_dare_agent_security_boundary.py tests/unit/test_five_layer_agent.py`: passed (`50 passed, 1 warning`) after the new security-gate integration coverage landed, confirming the added integration assertions do not regress the existing direct runtime and no-planner approval semantics.
- `../../.venv/bin/python -m pytest -q tests/unit/test_p0_gate_ci.py`: passed (`4 passed`) after extending the CI-side unit contract so `p0-gate` also preserves node ids from pytest `ERROR` summary lines, not only assertion-style `FAILED` lines.
- `../../.venv/bin/python scripts/ci/p0_gate.py`: passed and emitted:
  `p0-gate: PASS`
  `- SECURITY_REGRESSION: 0 failures`
  `- STEP_EXEC_REGRESSION: 0 failures`
  `- AUDIT_CHAIN_REGRESSION: 0 failures`
  which confirms the repository now has a single deterministic command entrypoint for the three frozen P0 categories.
- `openspec validate p0-conformance-gate --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues) after restoring the missing active feature aggregation record for this change.
- `./scripts/ci/check_governance_evidence_truth.sh`: initially failed because the restored feature doc lacked historical PR/review links; after linking the already-landed P0 evidence PRs, the governance gate passed, and remained green after task `1.1-1.3` synchronized the gate scope matrix and rollout contract into the active docs/spec set.
- `./scripts/ci/check_governance_evidence_truth.sh`: remained green after adding `docs/guides/P0_Gate_Runbook.md` plus the new navigation links in `docs/README.md` and `docs/guides/Team_Agent_Collab_Playbook.md`, confirming the operationalization docs did not break the governance acceptance pack.

### Behavior Verification

- Happy path: the existing contract-focused transport / interaction / example CLI suites still pass from a clean `origin/main` baseline, so the previously landed P0 contract assertions remain intact before new gate work begins.
- Error branch: the baseline suite still includes the approval action normalization and structured failure-contract assertions captured by tasks `2.4` and `5.1`, which are the current minimal regression anchors for `p0-gate`.
- Happy path: task `1.1-1.3` now defines a stable three-category matrix with explicit ownership modules, anchor suites, and required-mode thresholds, so later CI wiring can attach to a fixed scope instead of an ad hoc test grab-bag.
- Error branch: the rollout contract now explicitly blocks promoting `p0-gate` to a required check if any category lacks a green anchor set or emits uncategorized failures, preventing partial rollout from being misread as full P0 coverage.
- Happy path: task `2.1` now proves the security gate allows low-risk tool execution without creating pending approvals and still preserves the existing approval-required flow for high-risk execution.
- Error branch: task `2.1` now proves a denied capability is blocked before gateway invocation and recorded as a structured `not_allow` tool result inside the full agent flow, not only in direct `_run_tool_loop` unit tests.
- Happy path: task `2.2` now proves `step_driven` mode can complete a full session-loop closed loop with a planner and validator, preserve step order, and pass `_previous_output` from the first validated step into the second step during actual runtime execution.
- Error branch: task `2.2` now proves a failed first validated step aborts the remaining step sequence within the same milestone attempt and reaches `verify_milestone` as a structured failed run result instead of continuing to later steps.
- Happy path: task `2.3` now proves the default SQLite runtime event log can replay a real session window from `session.start` through later runtime events while keeping per-event `task_id` / `run_id` / `session_id` correlation intact.
- Error branch: task `2.3` now proves the same runtime-backed SQLite log fails `verify_chain()` after on-disk payload tampering, so the audit-chain invariant is validated against actual session data rather than only synthetic unit fixtures.
- Happy path: task `3.1` now exposes a single CI command entrypoint, `python scripts/ci/p0_gate.py`, that runs the three category bundles without relying on ad hoc workflow-local command duplication.
- Error branch: task `3.3` now guarantees failed `p0-gate` runs produce deterministic category-tagged triage output with failing node ids, module ownership, and first-action guidance instead of raw pytest noise alone.
- Error branch: the latest PR review fix now keeps deterministic node ids even when pytest stops in collection/import/runtime with `ERROR` summary lines, so CI triage does not collapse to `<no failing test ids captured>` for non-assertion failures.
- Happy path: tasks `4.1-4.3` now publish a single runbook that tells contributors exactly how to run `p0-gate`, where to look first for each category, how to archive release evidence, and how to record flaky incidents without inventing a second workflow.
- Error branch: the runbook now forbids silent anchor removal and silent rerun-based “fixes”; failed `p0-gate` runs must either be repaired or escalated through the documented flaky/quarantine path with owner and expiry.

### Risks and Rollback

- Risk: this change currently has partial task completion but had no active feature aggregation record, which weakens traceability until the governance baseline is restored.
- Risk: task `3.2` still depends on repo-admin branch protection / ruleset changes outside the repository, so `p0-gate` is not yet a true protected-branch merge blocker even though the job and summary contract now exist in-tree.
- Risk: `3.2` is now the only remaining open task in this change, and it cannot be completed from the repository contents alone.
- Rollback: if the new `p0-gate` workflow job proves too noisy before repo-admin rollout, remove the job entry from `.github/workflows/ci-gate.yml` and keep `scripts/ci/p0_gate.py` plus the runbook as local-only tooling until the category bundle is re-tuned.
- Rollback: no runtime behavior changed in this kickoff step; reverting only removes the restored governance record for the active change.

### Review and Merge Gate Links

- Current continuation branch: `codex/p0-conformance-gate`
- Historical PR for task `2.4`: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/130`
- Historical PR for task `5.1` baseline recovery path: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/113`
- Historical review evidence: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/130#pullrequestreview-3872526843`
- Historical merge evidence: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/130`
- PR status for this continuation branch: not opened yet

## Next Milestone

Schedule the repo-admin follow-up for task `3.2`: add `p0-gate` to the protected-branch required checks / ruleset after this change merges.
