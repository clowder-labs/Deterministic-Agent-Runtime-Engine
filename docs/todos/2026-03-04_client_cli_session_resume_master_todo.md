---
change_ids: ["client-session-resume"]
doc_kind: todo
topics: ["client-cli", "session-resume", "conversation-history", "t5-1"]
created: 2026-03-04
updated: 2026-03-04
status: active
mode: openspec
---

# 2026-03-04 Client CLI Session Resume Master TODO

> 来源：`docs/todos/2026-03-04_client_cli_session_resume_gap_analysis.md`
> 执行模型：docs baseline -> OpenSpec slice -> docs-only intent PR -> implementation -> evidence -> archive
> 范围：仅覆盖 `client/` 的跨进程会话恢复闭环

## 认领声明（Claim Ledger）

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-20260304-CRES-A | CRES-001~CRES-005 | codex | done | 2026-03-04 | 2026-03-07 | `client-session-resume` | 本地实现已补齐 resume + sessions list，后续仅剩真实 PR/review/archive 流程。 |

## 切片规划

| Slice | 目标 | 建议 OpenSpec Change | 主要覆盖 TODO |
|---|---|---|---|
| Slice A | 持久化 CLI session snapshot，补齐 `--resume` 与回归测试 | `client-session-resume` | CRES-001, CRES-002, CRES-003, CRES-004 |

## TODO 清单

| ID | Priority | Status | Gap ID | Planned OpenSpec Change | Task | Owner | Evidence | Last Updated |
|---|---|---|---|---|---|---|---|---|
| CRES-001 | P0 | done | CRES-GAP-001 | `client-session-resume` | 为 `client/` 增加 workspace 级 session snapshot store，持久化 `session_id`、`mode`、时间戳和 STM 消息。 | codex | `client/session_store.py`；`client/main.py`；`docs/features/client-session-resume.md` | 2026-03-04 |
| CRES-002 | P0 | done | CRES-GAP-002 | `client-session-resume` | 为 `chat/run/script` 增加 `--resume [session-id|latest]`，并在启动时输出/暴露当前 session id。 | codex | `client/main.py`；`client/README.md`；`client/DESIGN.md` | 2026-03-04 |
| CRES-003 | P1 | done | CRES-GAP-003 | `client-session-resume` | 明确恢复边界：恢复历史与 mode，不恢复 running task / pending approvals / pending plan，并将恢复后状态归一到 `idle`。 | codex | `client/DESIGN.md`；`openspec/changes/client-session-resume/design.md` | 2026-03-04 |
| CRES-004 | P0 | done | CRES-GAP-004 | `client-session-resume` | 新增 unit/integration 测试，覆盖 snapshot 持久化、latest 选择、指定 session 恢复、缺失 session 错误。 | codex | `tests/unit/test_client_cli.py`；`tests/integration/test_client_cli_flow.py` | 2026-03-04 |
| CRES-005 | P1 | done | CRES-GAP-005 | `client-session-resume` | 增加 `dare sessions list` 与交互态 `/sessions list`，输出当前 workspace 可恢复 session 摘要。 | codex | `client/session_store.py`；`client/main.py`；`tests/unit/test_client_cli.py`；`tests/integration/test_client_cli_flow.py`；`client/README.md` | 2026-03-04 |

## 执行规则

1. 先更新 `client/DESIGN.md` / `client/README.md` 与 OpenSpec artifacts，再开始代码实现。
2. `resume` 仅代表“恢复历史对话”，不代表 runtime checkpoint 断点续跑。
3. 任何恢复后的 CLI state 都必须从 `idle` 开始，不允许伪造“仍在运行”的状态。
4. `docs/features/client-session-resume.md` 必须作为该切片的单一状态与证据真相源。

## 建议验收边界

- `chat --resume` 能恢复最近一次 session 的历史消息并继续多轮对话。
- `run/script --resume <session>` 能在已有历史上下文上追加执行。
- `--resume` 找不到 session 时返回确定性参数错误。
- snapshot 文件损坏时返回清晰错误，而不是静默新建空会话。
