## Why

当前 `client/` 的多轮上下文只在同一进程里成立。`chat` 里继续追问是有效的，但 CLI 一退出，历史 STM、`conversation_id` 与执行模式就全部丢失，用户无法像 Claude Code / Codex CLI 那样“第二次打开继续上一次会话”。

当前基线存在三个实际缺口：

1. 没有 workspace 级 session snapshot，`conversation_id` 只是 metadata 标签，不是可恢复状态。
2. 没有 `--resume` 命令面，用户无法恢复最近一次或指定 session。
3. 没有明确恢复边界，后续实现容易把 pending approvals / running task / pending plan 等进程内瞬态误当作可恢复状态。

因此本切片收敛到一件事：为 `client/` 增加“跨进程恢复同一条对话”的基础能力，并用文档与回归测试把它冻结下来。

## What Changes

- 新增 workspace 级 session snapshot store，持久化最小可恢复 CLI state。
- 为 `chat/run/script` 增加 `--resume [session-id|latest]`。
- 增加 `sessions list` / `/sessions list`，让用户发现当前 workspace 的 resumable sessions。
- 恢复时回灌 STM/history 与 `mode`，并重置 CLI status 到 `idle`。
- 增加 unit/integration 测试，覆盖 latest 选择、指定 session 恢复、缺失 session 错误与 resume 后继续执行。
- 回写 `client/DESIGN.md`、`client/README.md`、feature evidence 与 TODO/OpenSpec artifacts。

## Capabilities

### Modified Capabilities

- `client-host-orchestration`: CLI invocation gains deterministic cross-process session restore semantics without changing the headless event/control contract.

## Impact

- 影响文件：
  - `client/main.py`
  - `client/session.py`
  - `client/session_store.py`
  - `client/DESIGN.md`
  - `client/README.md`
  - `tests/unit/test_client_cli.py`
  - `tests/integration/test_client_cli_flow.py`
  - `docs/features/client-session-resume.md`
  - `openspec/changes/client-session-resume/**`
- 不包含：
  - runtime checkpoint resume
  - paused execution / approval wait 恢复
  - startup handshake replay 或 event log replay
