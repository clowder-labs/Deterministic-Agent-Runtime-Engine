# Client Session Resume Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Claude/Codex-style basic resume support to `client/` by persisting CLI session history and restoring it across process restarts.

**Architecture:** Keep the runtime model unchanged and persist only CLI-owned session state. Use a file-backed session snapshot store under workspace `.dare/sessions/`, restore STM/history into the freshly bootstrapped agent context, and expose resume through explicit CLI flags instead of implicit auto-loading.

**Tech Stack:** Python `argparse`, JSON file persistence, existing `Context` STM APIs, pytest unit/integration coverage, OpenSpec docs.

---

### Task 1: Freeze docs-first resume semantics

**Files:**
- Create: `docs/todos/2026-03-04_client_cli_session_resume_gap_analysis.md`
- Create: `docs/todos/2026-03-04_client_cli_session_resume_master_todo.md`
- Create: `docs/features/client-session-resume.md`
- Create: `openspec/changes/client-session-resume/proposal.md`
- Create: `openspec/changes/client-session-resume/design.md`
- Create: `openspec/changes/client-session-resume/tasks.md`
- Create: `openspec/changes/client-session-resume/specs/client-host-orchestration/spec.md`
- Modify: `client/DESIGN.md`
- Modify: `client/README.md`

**Step 1: Write the failing test**

No code test in this task. This is the docs-first prerequisite.

**Step 2: Run verification**

Run: `openspec validate client-session-resume --strict`
Expected: PASS after artifacts are created.

**Step 3: Write minimal implementation**

Document the scope as “cross-process conversation resume”, not runtime checkpoint resume. Lock the CLI surface to `--resume [session-id|latest]` and the restore boundary to STM/history + mode only.

### Task 2: Add failing tests for session persistence and restore

**Files:**
- Modify: `tests/unit/test_client_cli.py`
- Modify: `tests/integration/test_client_cli_flow.py`

**Step 1: Write the failing test**

Add tests that expect:
- session snapshots to be written under workspace `.dare/sessions/`
- `chat/run/script --resume` to restore the previous session id and STM history
- `--resume` without an existing snapshot to fail deterministically

**Step 2: Run test to verify it fails**

Run:
- `.venv/bin/python -m pytest -q tests/unit/test_client_cli.py -k resume`
- `.venv/bin/python -m pytest -q tests/integration/test_client_cli_flow.py -k resume`

Expected: FAIL because no session store or resume parser path exists yet.

### Task 3: Implement the minimal session store and resume path

**Files:**
- Create: `client/session_store.py`
- Modify: `client/main.py`
- Modify: `client/session.py`

**Step 1: Write minimal implementation**

Implement a file-backed store that serializes STM messages plus minimal session metadata, restore it into the bootstrapped runtime context before the next task executes, and save snapshots after each completed CLI turn.

**Step 2: Run test to verify it passes**

Run:
- `.venv/bin/python -m pytest -q tests/unit/test_client_cli.py -k resume`
- `.venv/bin/python -m pytest -q tests/integration/test_client_cli_flow.py -k resume`

Expected: PASS

### Task 4: Sync docs and run focused verification

**Files:**
- Modify: `docs/features/client-session-resume.md`
- Modify: `openspec/changes/client-session-resume/tasks.md`
- Modify: `client/DESIGN.md`
- Modify: `client/README.md`

**Step 1: Run verification**

Run:
- `.venv/bin/python -m pytest -q tests/unit/test_client_cli.py`
- `.venv/bin/python -m pytest -q tests/integration/test_client_cli_flow.py`
- `openspec validate client-session-resume --strict`
- `./scripts/ci/check_governance_evidence_truth.sh`

Expected: PASS

**Step 2: Write minimal implementation**

Mark only completed tasks, replace placeholders in the feature evidence section with concrete commands/results, and document residual limitations around non-restored ephemeral runtime state.
