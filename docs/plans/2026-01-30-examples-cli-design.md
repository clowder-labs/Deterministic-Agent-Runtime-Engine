# Examples CLI Refresh Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver production-ready 01/02/03 examples with a readable, demo-quality CLI for 03 while keeping 01/02 minimal and correct.

**Architecture:** Keep 01/02 as simple builder-based entry points. Reintroduce a dedicated 03 CLI that wraps DareAgentBuilder and renders plan/execute flows with compact, human-readable output. Add a non-interactive demo script runner for deterministic presentation.

**Tech Stack:** Python 3.12, asyncio, dare_framework (builder + planner + validator + tools).

---

### Task 1: Audit and document current example state

**Files:**
- Read: `examples/01-basic-chat/README.md`
- Read: `examples/02-with-tools/README.md`
- Read: `examples/03-dare-coding-agent/README.md`
- Read: `examples/03-dare-coding-agent/main.py`
- Read: `examples/_archive/five-layer-coding-agent/*.py`

**Step 1: Capture gaps vs desired behavior**
- Document: missing CLI, unreadable output, outdated tool id handling, missing demo runner.

**Step 2: Save audit notes**
- Write brief notes in `docs/plans/2026-01-30-examples-cli-design.md` under “Audit Notes”.

---

### Task 2: Implement demo-grade CLI for 03 (builder-based)

**Files:**
- Create: `examples/03-dare-coding-agent/cli.py`
- Create: `examples/03-dare-coding-agent/demo_script.txt`
- Modify: `examples/03-dare-coding-agent/main.py`

**Step 1: Write failing tests (minimal) for CLI parsing & demo runner**
- Create: `tests/unit/test_examples_cli.py`
- Test: parse `/mode plan`, `/approve`, `/help`, `/quit`
- Test: demo runner reads script and feeds CLI loop

**Step 2: Run tests (expect failure)**
- Run: `pytest tests/unit/test_examples_cli.py -q`

**Step 3: Implement CLI (minimal pass)**
- Implement command parsing, session state, display renderer
- Support `/mode`, `/approve`, `/reject`, `/status`, `/help`, `/quit`
- Support `--demo demo_script.txt` and `--script <path>` for non-interactive run

**Step 4: Run tests (expect pass)**
- Run: `pytest tests/unit/test_examples_cli.py -q`

---

### Task 3: Update 03 README + demo instructions

**Files:**
- Modify: `examples/03-dare-coding-agent/README.md`

**Step 1: Update instructions**
- Emphasize builder usage, prompt management, tool names
- Add CLI usage and demo script instructions

---

### Task 4: Minimal corrections to 01/02

**Files:**
- Modify: `examples/01-basic-chat/README.md`
- Modify: `examples/02-with-tools/README.md`
- Modify: `examples/01-basic-chat/main.py`
- Modify: `examples/02-with-tools/main.py`

**Step 1: Clarify env & prompts**
- Note prompt store defaults (builder handles system prompts)
- Note tool names are used as capability ids (name uniqueness)

**Step 2: Keep code minimal**
- Avoid heavy CLI, keep /quit loop

---

### Task 5: Verification (targeted)

**Run:**
- `pytest tests/unit/test_examples_cli.py -q`
- `python examples/01-basic-chat/main.py` (manual)
- `python examples/02-with-tools/main.py` (manual)
- `python examples/03-dare-coding-agent/cli.py --demo examples/03-dare-coding-agent/demo_script.txt`

---

### Task 6: Commit

**Commit(s):**
- `feat(examples): add demo-grade CLI for dare coding agent`
- `docs(examples): refine readmes for 01/02/03`


---

## Audit Notes

- 01/02 README are minimal and omit prompt management behavior (builder injects `base.system`) and tool name uniqueness rules.
- 01/02 main.py are OK but should mention env defaults and avoid implying manual system prompts.
- 03 main.py is a single-shot runner with verbose ANSI output; not readable for demos and lacks interactive plan/execute flow.
- 03 README references `with_tools` (no such method) and omits CLI guidance and demo script.
- 03 main.py constructs `NativeToolProvider` but never uses it (tools are passed directly via builder).
- No demo script runner for deterministic presentation.
- Legacy CLI in `_archive/five-layer-coding-agent` is rich but uses old classes and tool IDs; needs re-implementation with current DareAgentBuilder.

---

### Task 2b: Fix execute loop context/tool messages (framework bug)

**Files:**
- Modify: `dare_framework/agent/_internal/five_layer.py`
- Test: `tests/unit/test_five_layer_agent.py`

**Step 1: Write failing test for tool result injection**
- Assert: tool call + tool result are appended to STM between iterations

**Step 2: Run test (expect failure)**
- Run: `pytest tests/unit/test_five_layer_agent.py::test_react_mode_with_tool_calls -q`

**Step 3: Implement fix**
- Add assistant message with tool_calls to STM
- Add tool result message to STM (role=tool, name=tool_call_id)
- Reassemble model input with updated STM

**Step 4: Run test (expect pass)**
- Run: `pytest tests/unit/test_five_layer_agent.py::test_react_mode_with_tool_calls -q`

---

### Task 2c: Fix DefaultRemediator prompt construction

**Files:**
- Modify: `dare_framework/plan/_internal/default_remediator.py`
- Test: `tests/unit/test_default_remediator.py`

**Step 1: Write failing test**
- Assert DefaultRemediator passes ModelInput to model.generate

**Step 2: Run test (expect failure)**
- Run: `pytest tests/unit/test_default_remediator.py -q`

**Step 3: Implement fix**
- Replace Prompt(messages=...) with ModelInput(messages=...)

**Step 4: Run test (expect pass)**
- Run: `pytest tests/unit/test_default_remediator.py -q`
