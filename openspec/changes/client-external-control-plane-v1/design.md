## Context

`client/` 现在已经具备宿主可读的 headless 事件面，但控制仍然留在进程内：

- CLI slash 命令直接调用本地 handler；
- `TransportActionClient` 直接通过 `DirectClientChannel.ask(...)` 进入 action/control；
- 宿主无法在同一 headless run 外部发送结构化审批或 MCP 请求。

Issue #135 的 Slice C 需要补足“写路径”，但不应同时引入网络暴露面或新命名体系。因此 v1 设计收敛到：

1. 控制输入来自 `--control-stdin`；
2. 动作 id 继续复用 canonical `resource:action`；
3. CLI 只做协议桥接，不重写运行时 action 语义。

## Goals / Non-Goals

**Goals:**

- 为 headless `run/script` 提供可选的 `--control-stdin` 本地控制入口。
- 定义最小 command/result/error envelope 和请求关联规则。
- 覆盖 approvals、MCP、skills 和 status 的最小宿主控制面。
- 对未知 action、非法参数、运行时失败给出结构化错误。

**Non-Goals:**

- 本次不实现 loopback RPC 或远程访问。
- 本次不实现 capability discovery 握手；`actions:list` 留给 Slice D。
- 本次不把 CLI-only `mcp unload` 暴露为宿主协议动作。
- 本次不改变 Slice B 已落地的 headless event envelope 格式。

## Decisions

### Decision 1: v1 只支持 `--control-stdin`

- 宿主在启动 headless `run/script` 时显式打开 `--control-stdin`。
- stdin 按“一行一个 JSON command frame”解析，不与 `chat` prompt 复用。
- 未启用 `--control-stdin` 时，headless 保持 Slice B 的只读事件语义。

### Decision 2: command/result/error envelope 与 headless event envelope 分离

- command frame 顶层字段至少包含：
  - `schema_version`
  - `id`
  - `action`
  - `params`
- result frame 顶层字段至少包含：
  - `schema_version`
  - `id`
  - `ok`
  - `result`
  - `error`
- 结果帧不复用 `event` 字段，避免把控制往返混入只读事件流语义。

### Decision 3: v1 action 范围收敛到现有 canonical surface

- 首批桥接 action：
  - `approvals:list`
  - `approvals:poll`
  - `approvals:grant`
  - `approvals:deny`
  - `approvals:revoke`
  - `mcp:list`
  - `mcp:reload`
  - `mcp:show-tool`
  - `skills:list`
  - `status:get`
- `status:get` 由 CLI session state 提供结构化快照；其余 action 复用现有运行时 handler。
- `mcp:unload` 继续留在 CLI 命令面，不进入 v1 协议基线。

### Decision 4: 错误必须结构化且不可回落为 prompt UX

- JSON 解析失败、未知 action、缺失参数、运行时 handler 失败都返回 `ok=false` 的结构化 error。
- 启用了 `--control-stdin` 的 headless 会话不得把控制错误打印成仅人类可读的交互提示。
- 审批已超时或 session 已结束时，control 响应仍需给出确定性错误码。

## Risks / Trade-offs

- [Risk] 同一个进程同时消费 task stdin 和 control stdin 会产生边界混淆。  
  → Mitigation: v1 仅允许 `run/script` 使用 `--control-stdin`，不让 `chat` 混入这条路径。

- [Risk] `status:get` 不是现有 runtime canonical action。  
  → Mitigation: 明确它是 CLI 宿主协议层动作，由 session state 投影，不伪装成 transport runtime action。

- [Risk] MCP 命令面当前支持 `unload`，但 canonical action 不支持。  
  → Mitigation: v1 只桥接 `mcp:list/reload/show-tool`，把 `unload` 明确留给后续 canonicalization。

## Migration Plan

1. 在 CLI 参数层增加 `--control-stdin`，限定其只作用于 headless `run/script`。
2. 增加 control frame 解析/分发/响应逻辑，并桥接现有 approvals、skills、MCP 和 status handler。
3. 为 happy path、unknown action、handler failure、session-lifecycle edge case 增加测试。
4. 回写 feature evidence、TODO ledger 与 OpenSpec task 状态。

## Open Questions

- control result/error 是否输出到 stdout 还是 stderr，才能兼容宿主同时读取事件流与控制响应？
- `status:get` 的最小返回字段是否应包含 `mode/status/running/active_task/pending_approvals`？
- `mcp:show-tool` 与现有 `/mcp inspect` 的输出投影是否需要完全一致，还是先只保证结构化字段稳定？
