---
change_ids: ["client-session-resume"]
doc_kind: analysis
topics: ["client-cli", "session-resume", "conversation-history", "t5-1"]
created: 2026-03-04
updated: 2026-03-05
status: active
mode: openspec
---

# 2026-03-04 DARE Client CLI Session Resume Gap Analysis

> 类型：专题 gap 分析
> 范围：`client/` 的跨进程会话恢复能力，目标对齐 Claude Code / Codex CLI 的基础“退出后继续同一会话”体验
> 上游治理项：`docs/todos/project_overall_todos.md` 中 `T5-1 session 管理下 context 持久化与跨会话交接闭环`
> 评审基线：`client/main.py`、`client/session.py`、`client/DESIGN.md`、`client/README.md`、`tests/unit/test_client_cli.py`、`tests/integration/test_client_cli_flow.py`

---

## 1. 先纠偏

当前 `client/` 里已经有 `conversation_id` / `session_id` 概念，但它只解决“同一进程内的关联标识”，不等于真正的 `resume`。

当前实现的真实语义是：

1. `client/main.py` 在每次 `chat/run/script` 启动时都会创建新的 `CLISessionState`。
2. `run_task(...)` 只把 `conversation_id` 放进 `Task.metadata`，并不会把历史会话从磁盘恢复回来。
3. `DareAgent` 的 STM 会在同一进程中跨轮保留，因此单次 `chat` 里多轮对话有上下文。
4. 进程一退出，CLI 没有任何 session snapshot、history manifest 或 `--resume` 入口，跨进程连续性完全丢失。

因此，对用户问题的直接回答是：

- 目前没有真正可用的 CLI `resume` 能力。
- 现有能力只是“运行中的内存会话连续”，不是“退出后恢复历史继续聊”。

---

## 2. 当前结论

- 本次应实现的 `resume` 语义应收敛为：恢复历史消息与 session identity，继续同一条 CLI 对话。
- 本次不扩成 runtime checkpoint / paused execution 断点续跑；那是 `IExecutionControl.resume()` 的另一条能力线。
- 最小可用闭环需要同时补：
  - session snapshot 持久化
  - `chat/run/script` 的 resume 入口
  - 缺失 / 损坏 snapshot 的确定性错误语义
  - 文档与回归测试

---

## 3. Gap 明细

| Gap ID | 设计声明（Design Claim） | 代码现状（Code Evidence） | 影响评估（Impact） | 建议动作（Action） | 优先级 |
|---|---|---|---|---|---|
| CRES-GAP-001 | CLI session 应能把可恢复的对话状态持久化到确定路径，而不是仅在内存里维持。 | `client/session.py` 只有 `CLISessionState` 内存结构；`client/main.py` 在每次入口都新建 state；仓库内没有 `client` 专用 session store。 | 用户关闭 CLI 后无法继续上一次任务上下文，体验与 Claude/Codex CLI 有明显差距。 | 为 `client/` 增加文件型 session snapshot store，至少持久化 `session_id`、`mode`、更新时间和 STM 消息列表。 | P0 |
| CRES-GAP-002 | CLI 应提供显式 resume 入口，支持恢复最近一次或指定 session。 | `client/_build_parser()` 只有 `chat/run/script`，没有 `--resume` 或等价入口。 | 即使后续补了持久化，用户仍没有稳定命令面去恢复会话。 | 为 `chat/run/script` 增加 `--resume [session-id|latest]`，空参数时默认 `latest`。 | P0 |
| CRES-GAP-003 | Resume 必须定义“恢复什么、不恢复什么”的边界，避免把进程内瞬态状态误当作可恢复状态。 | 当前没有任何 resume 语义；`pending_plan`、后台 task、待审批 request 都只存在内存。 | 若不声明边界，后续实现容易错误恢复 pending approvals / running task，造成状态不一致。 | 在设计与实现中明确：恢复 STM/history 和 mode；不恢复运行中任务、待审批队列、pending plan 预览；恢复后 session 状态重置为 `idle`。 | P1 |
| CRES-GAP-004 | Resume 需要设计级与测试级冻结，保证后续 CLI 演进不会回退。 | 现有 `tests/unit/test_client_cli.py` 与 `tests/integration/test_client_cli_flow.py` 没有 session snapshot / resume 覆盖。 | 没有回归面时，后续改命令行或 runtime bootstrapping 时极易再次丢失恢复能力。 | 增加 unit + integration 测试，覆盖 snapshot 持久化、latest 选择、特定 session 恢复、缺失 session 错误。 | P0 |
| CRES-GAP-005 | 用户应能枚举当前 workspace 的可恢复 session，而不是手动遍历 `.dare/sessions/`。 | 当前虽然已有 snapshot 文件，但 CLI 没有 `sessions list` 或等价入口。 | `resume` 已可用，但 discoverability 仍然差，用户不知道有哪些 session id 可恢复。 | 增加 `dare sessions list` 和交互态 `/sessions list`，返回按更新时间排序的 resumable session 摘要。 | P1 |
| CRES-GAP-006 | 外部宿主需要兼容 `--session-id` 语义，避免只能依赖新引入的 `--resume` 参数。 | 当前 `run/chat/script` 仅接受 `--resume`；`--session-id` 只在 approvals 子命令出现。 | Cat Cafe 等集成方需要做参数分支或改造调用协议，迁移成本升高。 | 在 `run/chat`（并保持 script 一致性）增加 `--session-id` 兼容入口并映射到同一 resume 语义；与 `--resume` 冲突时给确定性参数错误。 | P1 |
| CRES-GAP-007 | Headless 宿主控制面需要提供 `session:resume` 动作，支持基于 control-stdin 的会话恢复。 | 当前 `control-stdin` 支持 approvals/MCP/skills/status/actions list，但没有 `session:resume`。 | 宿主若走统一控制协议，无法在不改 CLI 启动参数的情况下恢复历史会话。 | 在 `--headless --control-stdin` 下增加 `session:resume`，恢复 session history + session id，并把该动作纳入 `actions:list`。 | P1 |

---

## 4. 影响范围

### 4.1 设计与文档

- `client/DESIGN.md`
- `client/README.md`
- `docs/features/client-session-resume.md`
- `openspec/changes/client-session-resume/**`

### 4.2 实现

- `client/main.py`
- `client/session.py`
- `client/runtime/task_runner.py`
- 新增 `client/session_store.py`（或等价持久化模块）

### 4.3 测试

- `tests/unit/test_client_cli.py`
- `tests/integration/test_client_cli_flow.py`
- 可选新增独立 session store 单元测试文件

---

## 5. 建议切片

本轮收敛为单一切片：

1. Slice A: `client-session-resume`
   - 目标：补齐跨进程 session snapshot + resume 命令面 + 回归测试
   - 不包含：checkpoint resume、审批等待恢复、startup handshake replay

---

## 6. 风险提示

1. 若直接恢复内存态字段（如 pending approval / running task），会制造“磁盘状态与真实 runtime 状态不一致”的假恢复。
2. 若不把 snapshot 路径固定到 workspace `.dare/sessions/`，用户将很难判断 resume 的作用域。
3. 若不覆盖 `latest` 选择和损坏文件错误路径，`resume` 体验会不稳定且难排查。

---

## 7. 本轮结论

- 用户要求的 `resume` 能力当前不存在。
- 最合理的第一版实现是：`chat/run/script` 共享一套 session snapshot store，并通过 `--resume` 恢复历史消息与 `session_id`。
- 下一步进入 master TODO、OpenSpec artifacts 和 failing tests。
