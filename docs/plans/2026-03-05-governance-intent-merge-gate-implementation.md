# Governance Intent-Merge Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce a hard CI gate that blocks implementation PRs unless an Intent PR is explicitly linked and already merged.

**Architecture:** Add a dedicated diff-aware shell gate (`check_governance_intent_gate.sh`) that detects implementation-path changes, requires governed `docs/features/*.md` updates in the same PR, extracts `Intent PR` links, and validates merged status through deterministic fixtures (tests) or GitHub API (CI). Wire the gate into `ci-gate` as a required PR/merge-group check.

**Tech Stack:** Bash gate scripts, Git diff metadata, GitHub REST API (`pulls/{number}`), Python unittest regression tests, GitHub Actions.

---

### Task 1: Add failing regression tests for intent-merge gate behavior

**Files:**
- Create: `tests/unit/test_governance_intent_gate.py`

**Step 1: Write the failing test**

Add tests that expect:
- docs-only changes skip the gate;
- implementation changes without governed feature doc update fail;
- implementation changes with unmerged intent PR fail;
- implementation changes with merged intent PR pass.

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/unit/test_governance_intent_gate.py`
Expected: FAIL because gate script does not exist yet.

### Task 2: Implement the gate script and satisfy tests

**Files:**
- Create: `scripts/ci/check_governance_intent_gate.sh`

**Step 1: Write minimal implementation**

Implement:
- diff range resolution (`GOVERNANCE_INTENT_GATE_CHANGED_FILES` fixture override, then PR-base diff fallback);
- implementation-path detection vs governance-only paths;
- governed feature-doc requirement and status filter (`active|in_review|in-review`);
- intent PR link extraction and merged-state validation (fixture first, GitHub API fallback with `GITHUB_TOKEN`).

**Step 2: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/unit/test_governance_intent_gate.py`
Expected: PASS

### Task 3: Wire CI and sync governance docs

**Files:**
- Modify: `.github/workflows/ci-gate.yml`
- Modify: `docs/guides/Development_Constraints.md`
- Modify: `docs/guides/Documentation_First_Development_SOP.md`
- Modify: `docs/guides/Evidence_Truth_Implementation_Strategy.md`
- Modify: `docs/features/enhance-doc-governance-traceability.md`
- Modify: `openspec/changes/enhance-doc-governance-traceability/tasks.md`

**Step 1: Run verification**

Run:
- `.venv/bin/python -m pytest -q tests/unit/test_governance_intent_gate.py tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`
- `./scripts/ci/check_governance_intent_gate.sh` (with fixture env for local deterministic run)

Expected: PASS

**Step 2: Write minimal implementation**

Document the new hard gate as the canonical “intent merged before implementation” enforcement, including command-of-record and CI wiring.
