---
change_ids: ["client-session-resume"]
doc_kind: feature
topics: ["client-cli", "session-resume", "conversation-history", "t5-1"]
todo_ids: ["CRES-001", "CRES-002", "CRES-003", "CRES-004", "CRES-005", "CRES-006", "CRES-007"]
created: 2026-03-04
updated: 2026-03-05
status: draft
mode: openspec
---

# Feature: client-session-resume

## Scope

为 `client/` 补齐跨进程会话恢复能力：把当前仅存在于进程内的 STM/history 持久化到 workspace session snapshot，并通过 `--resume [session-id|latest]` 与 `--session-id` 兼容入口在后续 `chat/run/script` 启动时恢复同一条对话；同时补 `sessions list` 与 `session:resume` control action，支持发现与外部宿主恢复。

## OpenSpec Artifacts

- Proposal: `openspec/changes/client-session-resume/proposal.md`
- Design: `openspec/changes/client-session-resume/design.md`
- Specs:
  - `openspec/changes/client-session-resume/specs/client-host-orchestration/spec.md`
- Tasks: `openspec/changes/client-session-resume/tasks.md`

## Governance Anchors

- `docs/guides/Development_Constraints.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `docs/todos/2026-03-04_client_cli_session_resume_gap_analysis.md`
- `docs/todos/2026-03-04_client_cli_session_resume_master_todo.md`
- `client/DESIGN.md`
- `client/README.md`

## Evidence

### Commands

- `.venv/bin/python -m pytest -q tests/unit/test_client_cli.py -k resume`
- `.venv/bin/python -m pytest -q tests/integration/test_client_cli_flow.py -k resume`
- `.venv/bin/python -m pytest -q tests/unit/test_client_cli.py -k 'session_id_flag or conflicting_resume_and_session_id or dispatch_control_action_session_resume'`
- `.venv/bin/python -m pytest -q tests/integration/test_client_cli_flow.py -k 'session_resume or bridges_actions_list or coexists_with_existing_control_actions or bridges_additional_host_actions'`
- `.venv/bin/python -m pytest -q tests/unit/test_client_cli.py`
- `.venv/bin/python -m pytest -q tests/integration/test_client_cli_flow.py`
- `openspec validate client-session-resume`
- `./scripts/ci/check_governance_traceability.sh`
- `./scripts/ci/check_governance_evidence_truth.sh`

### Results

- `tests/unit/test_client_cli.py -k resume`: passed (`2` tests),确认 parser 能识别 `--resume`，且缺失 session 时返回确定性错误。
- `tests/integration/test_client_cli_flow.py -k resume`: passed (`2` tests)，确认 first run 会写 snapshot，second run 能用 `latest` 或显式 `session-id` 恢复历史和原 session id。
- `tests/unit/test_client_cli.py -k 'session_id_flag or conflicting_resume_and_session_id or dispatch_control_action_session_resume'`: passed (`4` tests)，覆盖 `--session-id` parser、`--resume/--session-id` 冲突参数错误、`session:resume` success/error 分支。
- `tests/integration/test_client_cli_flow.py -k 'session_resume or bridges_actions_list or coexists_with_existing_control_actions or bridges_additional_host_actions'`: passed (`8` tests)，覆盖 `actions:list` 暴露 `session:resume` 以及 headless 运行中调用的结构化拒绝分支。
- `tests/unit/test_client_cli.py`: passed (`56` tests)，包含 session resume + sessions list + issue #184 兼容与控制面回归。
- `tests/integration/test_client_cli_flow.py`: passed (`29` tests)，包含脚本态 `/sessions list`、headless `session:resume` 与 capability discovery 回归。
- `openspec validate client-session-resume`: passed。
- `./scripts/ci/check_governance_traceability.sh`: passed。
- `./scripts/ci/check_governance_evidence_truth.sh`: active 模式下会因缺少 intent/implementation PR 与 review link 失败；本地实现阶段将本文档保持为 `draft`，待真正进入 review/merge gate 时再补齐链接并切到 `active` / `in_review`。

### Behavior Verification

- Happy path: `run --task "first task"` 结束后会在 workspace `.dare/sessions/` 落 snapshot；随后 `run --resume latest --task "follow up"`、`run --resume <session-id> --task "follow up"` 或 `run --session-id <session-id> --task "follow up"` 会先恢复历史 STM，再继续执行，并复用原 session id。`sessions list` / `/sessions list` 会按最近更新时间列出当前 workspace 可恢复 session。
- Error/fallback path: `--resume latest` 在没有 snapshot 的 workspace 中会以参数错误退出；同时传 `--resume` 和 `--session-id` 且目标不一致时也会以参数错误退出。headless 控制面下，`session:resume` 在运行中会返回结构化 `INVALID_SESSION_STATE`。

### Risks and Rollback

- Risk: first version只恢复历史与 mode，不恢复 pending plan / approvals / running task，这与 runtime checkpoint resume 语义不同。
- Rollback: 回退 `client` 的 session store 与 `--resume` 入口，恢复到“每次启动都是新会话”的基线。

### Review and Merge Gate Links

- Intent PR: `pending`
- Implementation PR: `pending`
- Review thread: `pending`
