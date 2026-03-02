---
change_ids: ["client-external-control-plane-v1"]
doc_kind: feature
topics: ["client-cli", "host-orchestration", "control-plane", "issue-135"]
todo_ids: ["CCLI-005", "CCLI-006"]
created: 2026-03-02
updated: 2026-03-02
status: active
mode: openspec
---

# Feature: client-external-control-plane-v1

## Scope

落实 Issue #135 的 Slice C：为 `client/` 增加外部结构化 control plane v1，优先采用 `--control-stdin` 作为本地宿主入口，并覆盖审批、MCP、skills 与 session status 的最小控制面。

## OpenSpec Artifacts

- Proposal: `openspec/changes/client-external-control-plane-v1/proposal.md`
- Design: `openspec/changes/client-external-control-plane-v1/design.md`
- Specs:
  - `openspec/changes/client-external-control-plane-v1/specs/client-host-orchestration/spec.md`
- Tasks: `openspec/changes/client-external-control-plane-v1/tasks.md`

## TODO Coverage

- `CCLI-005`
- `CCLI-006`

## Evidence

### Commands

- `git fetch origin`
- `git worktree add .worktrees/client-external-control-plane-v1 -b codex/client-external-control-plane-v1 origin/main`
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q -k 'control_stdin or control-stdin or chat_parser_rejects_control_stdin_flag or run_and_script_parser_accept_control_stdin_flag'`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'control_stdin_status_get_emits_structured_result'`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'bridges_approvals_list'`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'bridges_additional_host_actions'`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'script_headless_control_stdin_status_get_reports_active_task'`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'surfaces_action_handler_failure or rejects_unsupported_action or bridges_approvals_list or control_stdin_status_get_emits_structured_result or script_headless_control_stdin_status_get_reports_active_task'`
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`
- `openspec list`
- `openspec validate client-external-control-plane-v1 --type change --strict --json --no-interactive`
- `./scripts/ci/check_governance_evidence_truth.sh`

### Results

- `git fetch origin`: confirmed `origin/main` includes merged Slice B via PR `#145`.
- `git worktree add .worktrees/client-external-control-plane-v1 -b codex/client-external-control-plane-v1 origin/main`: created an isolated Slice C workspace from `origin/main` commit `bc39bc0`.
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q -k 'control_stdin or control-stdin or chat_parser_rejects_control_stdin_flag or run_and_script_parser_accept_control_stdin_flag'`: passed (`4` tests) after adding `--control-stdin` parser support and rejecting non-headless usage.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'control_stdin_status_get_emits_structured_result'`: failed before the first control-loop implementation because no `client-control-stdin.v1` response frame was emitted; passed after landing the control stdin loop and `status:get` snapshot.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'bridges_approvals_list'`: failed before approvals were bridged through canonical action dispatch; passed after exposing `approvals:list` via the control plane.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'bridges_additional_host_actions'`: failed (`3` MCP cases red, `skills:list` already green) before `mcp:list/reload/show-tool` were admitted to the host bridge; passed (`4` tests) after extending the canonical action allow-list while keeping `mcp:unload` structurally rejected.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'script_headless_control_stdin_status_get_reports_active_task'`: failed before script foreground execution tracked `active_task`; passed after aligning script/session state with run-mode snapshots.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'surfaces_action_handler_failure or rejects_unsupported_action or bridges_approvals_list or control_stdin_status_get_emits_structured_result or script_headless_control_stdin_status_get_reports_active_task'`: passed (`5` tests), covering happy path plus unsupported-action and handler-failure branches.
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`: passed (`44` tests, `0` failures).
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`: passed (`20` tests, `0` failures).
- `openspec list`: confirms Slice A / Slice B have been archived out of the active change list, and the active Slice C change now shows `✓ Complete`.
- `openspec validate client-external-control-plane-v1 --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).
- `./scripts/ci/check_governance_evidence_truth.sh`: passed after the Slice C feature evidence block and prior-slice archive moves were synchronized.

### Behavior Verification

- Happy path: `run/script --headless --control-stdin` now multiplexes `client-control-stdin.v1` responses on stdout alongside the existing headless event envelope, and `status:get` returns a structured session snapshot including the current active task.
- Happy path: approvals are now reachable from the host control plane through the canonical `approvals:*` action ids, without falling back to slash-command parsing.
- Happy path: `skills:list` and canonical MCP actions `mcp:list/reload/show-tool` now return structured control results with request correlation, and `mcp:show-tool` preserves `mcp_name/tool_name` params across the bridge.
- Error branch: unsupported actions such as `mcp:unload` return structured `UNSUPPORTED_ACTION` errors, and transport/action handler failures are surfaced as structured error responses instead of prompt text.

### Risks and Rollback

- Risk: adding a second stdin consumer beside `chat` / `script` can create framing ambiguity if control and prompt input are not cleanly separated.
- Rollback: drop the Slice C kickoff change and keep the repository at the merged Slice B baseline where headless remains read-only.

### Review and Merge Gate Links

- Slice A intent gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/141`
- Slice B implementation gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145`
- Slice C docs-only intent PR (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/148`
- Slice C spec-fold review thread: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/148#discussion_r2872038646`
