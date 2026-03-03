# Enhance Doc Governance Traceability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the next real gaps in `enhance-doc-governance-traceability` by adding a reusable feature aggregation template, explicit active/archive feature indexes, a machine-checkable governance traceability gate, and one active pilot backfill.

**Architecture:** Keep the existing evidence-truth gate focused on feature evidence semantics, and add a separate traceability gate for document topology, metadata, and TODO/change linkage. Use one active feature doc as the pilot so the new checks prove the contract without forcing a full historical backfill.

**Tech Stack:** Markdown governance docs, shell CI scripts, Python unittest subprocess-based gate tests, GitHub Actions.

---

### Task 1: Define the docs/features governance surface

**Files:**
- Create: `docs/features/templates/feature_aggregation_template.md`
- Create: `docs/features/archive/README.md`
- Modify: `docs/features/README.md`
- Modify: `docs/README.md`

**Step 1: Write the failing test**

Add a gate test that expects:
- `docs/features/templates/feature_aggregation_template.md` to exist
- `docs/features/README.md` to reference the template and active entries section
- `docs/features/archive/README.md` to exist as the archive index

**Step 2: Run test to verify it fails**

Run: `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py -k template`
Expected: FAIL because the template/archive index gate does not exist yet.

**Step 3: Write minimal implementation**

Create the template and archive index, then update `docs/features/README.md` and `docs/README.md` so the feature-doc lifecycle is discoverable from the docs navigation.

**Step 4: Run test to verify it passes**

Run: `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py -k template`
Expected: PASS

### Task 2: Add the governance traceability CI gate

**Files:**
- Create: `scripts/ci/check_governance_traceability.sh`
- Create: `tests/unit/test_governance_traceability_gate.py`
- Modify: `.github/workflows/ci-gate.yml`

**Step 1: Write the failing test**

Add subprocess-based tests that create a temp docs tree and assert the new gate fails when:
- the template or archive index is missing
- active feature docs are not listed in the active index
- checkpoint-to-skill mapping is missing
- a declared `todo_ids` entry cannot be found in any TODO ledger for the same change

**Step 2: Run test to verify it fails**

Run: `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py`
Expected: FAIL with missing gate/script behavior.

**Step 3: Write minimal implementation**

Implement `scripts/ci/check_governance_traceability.sh` with repository-root override support and wire it into `ci-gate` as a dedicated job.

**Step 4: Run test to verify it passes**

Run: `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py`
Expected: PASS

### Task 3: Backfill one active pilot change

**Files:**
- Modify: `docs/features/agentscope-d2-d4-thinking-transport.md`

**Step 1: Write the failing test**

Extend the gate test so a pilot feature doc declaring `todo_ids` must be backed by a TODO ledger that contains both the same TODO ids and the owning change-id.

**Step 2: Run test to verify it fails**

Run: `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py -k todo`
Expected: FAIL until the pilot doc and gate are aligned.

**Step 3: Write minimal implementation**

Add `todo_ids` to `docs/features/agentscope-d2-d4-thinking-transport.md` using the already-declared `D2-*` / `D4-*` mapping in `docs/todos/agentscope_domain_execution_todos.md`.

**Step 4: Run test to verify it passes**

Run: `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py -k todo`
Expected: PASS

### Task 4: Sync the active governance change evidence

**Files:**
- Modify: `openspec/changes/enhance-doc-governance-traceability/tasks.md`
- Modify: `docs/features/enhance-doc-governance-traceability.md`

**Step 1: Write the failing test**

No new automated test. This step is evidence synchronization after the new gate is green.

**Step 2: Run verification**

Run:
- `../../.venv/bin/python -m pytest -q tests/unit/test_governance_traceability_gate.py tests/unit/test_governance_evidence_truth_gate.py`
- `./scripts/ci/check_governance_traceability.sh`
- `./scripts/ci/check_governance_evidence_truth.sh`
- `openspec validate enhance-doc-governance-traceability --type change --strict --json --no-interactive`

Expected: PASS

**Step 3: Write minimal implementation**

Mark only the tasks actually completed by this slice, and replace stale `openspec status` claims in the feature doc with fresh command results from this work.

**Step 4: Commit**

```bash
git add docs/features docs/README.md docs/plans/2026-03-03-enhance-doc-governance-traceability-implementation.md \
  scripts/ci/check_governance_traceability.sh tests/unit/test_governance_traceability_gate.py \
  .github/workflows/ci-gate.yml openspec/changes/enhance-doc-governance-traceability/tasks.md
git commit -m "feat(governance): add traceability gate baseline" -m "Add a feature aggregation template, active/archive feature indexes, a new governance traceability CI gate, and a pilot TODO-to-change backfill for an active change. This closes the next real gaps in enhance-doc-governance-traceability without forcing a broad historical docs rewrite."
```
