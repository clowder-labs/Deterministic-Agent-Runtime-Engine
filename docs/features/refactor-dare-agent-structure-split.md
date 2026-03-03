---
change_ids: ["refactor-dare-agent-structure-split"]
doc_kind: feature
topics: ["agent", "refactor", "orchestration", "testing"]
created: 2026-03-03
updated: 2026-03-03
status: active
mode: openspec
---

# Feature: refactor-dare-agent-structure-split

## Scope

完成 A-101 的最后一项收尾：在 `DareAgent` façade delegation 已拆分完成的前提下，为 `_internal` 的 `execute_engine`、`tool_executor`、`milestone_orchestrator` 补齐 direct unit tests，锁住 success/failure/approval/policy/retry 分支语义。

## OpenSpec Artifacts

- Proposal: `openspec/changes/refactor-dare-agent-structure-split/proposal.md`
- Design: `openspec/changes/refactor-dare-agent-structure-split/design.md`
- Tasks: `openspec/changes/refactor-dare-agent-structure-split/tasks.md`

## Governance Anchors

- `docs/design/modules/agent/TODO.md`
- `docs/design/TODO_INDEX.md`

## Evidence

### Commands

- `git worktree add .worktrees/refactor-dare-agent-structure-split -b codex/refactor-dare-agent-structure-split origin/main`
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py tests/unit/test_five_layer_agent.py tests/unit/test_dare_agent_hook_governance.py tests/unit/test_dare_agent_hook_transport_boundary.py`
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py -k 'before_model_hook_blocks or no_tool_calls or preflight_denies or done_predicate_is_satisfied or plan_policy_failure'`
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py::test_run_tool_loop_retries_until_done_predicate_is_satisfied`
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py`
- `../../.venv/bin/python -m pytest -q tests/unit/test_five_layer_agent.py tests/unit/test_dare_agent_hook_governance.py tests/unit/test_dare_agent_hook_transport_boundary.py`

### Results

- `git worktree add ... origin/main`: created an isolated continuation workspace for the final A-101 closeout from `origin/main` commit `5d1cfb4`.
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py tests/unit/test_five_layer_agent.py tests/unit/test_dare_agent_hook_governance.py tests/unit/test_dare_agent_hook_transport_boundary.py`: baseline passed (`43 passed, 1 warning`) before adding new tests, confirming the change started from a clean regression surface.
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py -k 'before_model_hook_blocks or no_tool_calls or preflight_denies or done_predicate_is_satisfied or plan_policy_failure'`: passed (`4 passed, 5 deselected, 1 warning`) after adding the new direct `_internal` branch coverage.
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py::test_run_tool_loop_retries_until_done_predicate_is_satisfied`: passed (`1 passed, 1 warning`) after the PR #163 review fix raised `max_calls` above the expected completion point, so the retry coverage now proves the loop exits on `done_predicate` satisfaction instead of coincidentally stopping at the budget ceiling.
- `../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_orchestration_split.py`: passed (`9 passed, 1 warning`) with both the existing façade delegation assertions and the new direct execution-unit tests.
- `../../.venv/bin/python -m pytest -q tests/unit/test_five_layer_agent.py tests/unit/test_dare_agent_hook_governance.py tests/unit/test_dare_agent_hook_transport_boundary.py`: passed (`39 passed, 1 warning`) after the new unit tests landed, confirming no regression on the previously accepted A-101 coverage surface.

### Behavior Verification

- Happy path: `_internal` execute logic now has a direct test proving model responses without tool calls finalize successfully and persist the assistant message into STM without going back through the `DareAgent` façade.
- Happy path: `_internal` tool execution now has a direct retry test proving `done_predicate` retries until the required output key is produced, while preserving the existing success result shape.
- Error branch: `_internal` execute/model hook block, tool preflight deny, and milestone plan-policy failure now each have direct tests asserting their structured failure payloads/events rather than relying on broader integration suites to catch drift.

### Risks and Rollback

- Risk: these tests use lightweight fake agents rather than full `DareAgent` instances, so future internal protocol expansion may require updating the fakes alongside implementation changes.
- Rollback: revert the new direct unit tests and tasks/docs evidence updates; production runtime behavior is unchanged by this slice.

### Review and Merge Gate Links

- Historical implementation PR (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/117`
- Historical owner feedback thread: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/117`
- Final verification PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/163`
- PR #163 review thread: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/163#discussion_r2875871921`
