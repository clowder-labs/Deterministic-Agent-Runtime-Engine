## Context

`client/` 当前已经有三块与 resume 相关但未闭环的基础设施：

- `CLISessionState` 维护 `mode/status/conversation_id` 等 CLI 级状态；
- `DareAgent.context` 的 STM 在单进程多轮里会持续保留用户/assistant/tool 消息；
- `run_task(...)` 会把 `conversation_id` 透传到 `Task.metadata`，用于审计与关联。

缺口在于：CLI 没有把这三部分变成可恢复的持久化资产。每次入口都会新建 state 和 runtime，历史上下文没有从磁盘回灌，因此 `conversation_id` 只是一层标签，而不是 resume contract。

## Goals / Non-Goals

**Goals:**

- 为 `client/` 定义并实现跨进程 session snapshot。
- 支持 `chat/run/script --resume [session-id|latest]`。
- 支持显式列出当前 workspace 下可恢复的 sessions。
- 恢复历史 STM 消息与 CLI mode，并复用原 session id。
- 对缺失 / 损坏 snapshot 提供确定性错误。

**Non-Goals:**

- 不实现 runtime checkpoint 或 paused execution 断点续跑。
- 不恢复 pending approvals、running task、pending plan preview。
- 不改 headless event envelope / control-stdin schema。
- 不引入远程 session store 或多 workspace 聚合索引。

## Decisions

### Decision 1: session snapshot 固定写入 workspace `.dare/sessions/`

- snapshot 目录固定为 `<workspace>/.dare/sessions/`。
- 每个 session 一个 JSON 文件，文件名使用 `session_id`。
- `latest` 通过扫描 snapshot 的 `updated_at` 选择最近一次写入。

这样可以保持作用域清晰：resume 只作用于当前 workspace，而不是跨仓库混用历史。

### Decision 2: 第一版只持久化“可安全恢复”的 CLI state

持久化内容：

- `session_id`
- `mode`
- `created_at`
- `updated_at`
- `workspace_dir`
- `messages`（STM 序列化结果）

不持久化内容：

- `status`
- `active_execution_task`
- `pending_runtime_approvals`
- `pending_plan`
- `pending_task_description`

原因是这些字段都依赖活跃进程或一次性 planner 结果，跨进程恢复会制造虚假状态。

### Decision 3: resume 后一律从 `idle` 重新开始

- 恢复成功后，CLI 会加载历史消息、恢复 `mode`，并把 `status` 归一到 `idle`。
- 若用户此前在 `plan` 模式下退出，恢复后仍保留 `plan` 模式，但不会恢复上一条 `pending_plan`。
- 后续新的用户输入会在恢复后的 STM 上继续执行。

### Decision 4: `--resume` 是显式入口，不做隐式自动恢复

- 不因为 workspace 里存在 snapshot 就自动 resume。
- 只有显式传入 `--resume` 才加载历史。
- `--resume` 不带值时默认选择 `latest`。

这样可以避免“本想开新会话却被自动加载旧历史”的歧义。

### Decision 5: session discovery 通过 `sessions list` 暴露

- 顶层命令增加 `dare sessions list`。
- 交互态增加 `/sessions list`。
- 返回结果按 `updated_at` 倒序，至少包含 `session_id`、`mode`、`updated_at`、`messages_count`、`path`。

这样用户不需要手动遍历 `.dare/sessions/`，也不需要猜测 session id。

## Data Structures

### SessionSnapshot

```json
{
  "schema_version": "client-session.v1",
  "session_id": "abc123",
  "mode": "execute",
  "created_at": 1772592000.0,
  "updated_at": 1772592030.0,
  "workspace_dir": "/abs/workspace",
  "messages": [
    {
      "role": "user",
      "content": "summarize README",
      "name": null,
      "metadata": {},
      "mark": "temporary",
      "id": null
    }
  ]
}
```

### RestoreResult

恢复内部结果至少需要提供：

- 解析后的 snapshot
- `restored_messages_count`
- 解析出的 `session_id`

供 CLI 启动日志/headless event 填充 resume metadata。

## Core Workflow

1. CLI 解析到 `--resume` 后，在 runtime bootstrapping 完成后加载 snapshot。
2. 将 snapshot 中的消息写入 `runtime.agent.context` 的 STM。
3. 用 snapshot 的 `session_id` 与 `mode` 构造 `CLISessionState`。
4. 运行新的 `chat/run/script` 输入。
5. 每次执行完成或关键状态变化后，把当前 STM 与最小 session metadata 写回 snapshot 文件。

## Key Interfaces

### `client/session_store.py`

- `load(resume_target: str) -> SessionSnapshot`
- `save(state: CLISessionState, messages: list[Message]) -> Path`
- `resolve_latest() -> str`
- `list_sessions() -> list[SessionListing]`

### `client/main.py`

- 解析 `--resume`
- 在 `chat/run/script` 入口决定是新建 session 还是恢复 session
- 执行后触发 snapshot 写回

## Error Handling

- `--resume` 目标不存在：返回参数错误（exit code `2`），提示 session id 或 latest 不可用。
- snapshot JSON 损坏：返回参数错误（exit code `2`），提示文件路径和解析失败原因。
- snapshot 版本不兼容：返回参数错误（exit code `2`），提示 schema version 不支持。
- snapshot 写回失败：返回业务错误（exit code `1`），因为执行结果可能已产生，但状态未能持久化。

## Risks / Trade-offs

- [Risk] 把 snapshot 放在 workspace 下意味着同一用户跨 workspace 不能共享 recent sessions。  
  -> Mitigation: 这与当前 CLI 的 workspace 作用域一致，先保守隔离。

- [Risk] 恢复 STM 但不恢复 pending plan，可能让部分用户觉得“没有完全接着上次继续”。  
  -> Mitigation: 文档里明确第一版语义是对话 history resume，不是 planner/runtime snapshot resume。

- [Risk] 长会话 snapshot 体积会增长。  
  -> Mitigation: 第一版保持最小实现；后续可与 `T5-1` 的压缩/summary 管线对接。

## Migration Plan

1. 先补 docs 与 OpenSpec artifacts，锁定 resume 边界。
2. 写 failing tests。
3. 实现 session store 与 parser/runtime resume。
4. 跑回归并回写 feature evidence。
