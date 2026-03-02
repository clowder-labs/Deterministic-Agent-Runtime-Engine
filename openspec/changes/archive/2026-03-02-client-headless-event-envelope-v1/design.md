## Context

PR `#141` 已经把 `client/` 的宿主编排基线文档合入 `main`，并明确区分了 `interactive`、`automation-json`、`headless` 三个模式层级。当前主干仍只有前两类 landed 行为：`chat` 可以交互提示，`run/script --output json` 可以输出 `log/event/result` 行，但还没有真正的 headless contract。

Slice B 的目标是实现最小可依赖的“非交互事件面”：

- 宿主可以显式进入 headless 模式；
- CLI 不再回落到 prompt / inline approval；
- 宿主收到的是 versioned、可关联的事件帧，而不是 legacy automation JSON。

## Goals / Non-Goals

**Goals:**

- 为 `run` / `script` 增加显式 `--headless` 入口。
- 实现 event envelope v1，并与 legacy automation JSON 分离。
- 明确 headless 下审批不可内联处理时的结构化失败语义。
- 为 headless happy path 与 changed error branch 增加测试覆盖。

**Non-Goals:**

- 本次不实现外部 control plane。
- 本次不实现 capability discovery 握手。
- 本次不改变现有 `--output json` 的行格式契约。
- 本次不让 `chat` 支持 headless。

## Decisions

### Decision 1: `--headless` 是显式模式开关，且只允许 `run` / `script` 使用

- `chat` 继续保持交互语义，不接收 `--headless`。
- `run` / `script` 在 `--headless` 下进入独立输出路径，不依赖当前 `--output human|json`。
- `--headless` 与 legacy `--output` 组合时，CLI 应返回确定性的参数错误，而不是静默降级。

### Decision 2: headless 模式下禁止 prompt 与内联审批回落

- 任何 `dare>` 或 `approve>` 样式的人类交互提示都不得出现在 headless stdout/stderr。
- 当执行遇到审批要求且当前 Slice 尚未提供控制面时，CLI 必须输出结构化错误事件并以非零状态退出。
- 允许先发出 `approval.pending` 事件，只要后续失败路径仍保持结构化并且不要求用户输入。

### Decision 3: event envelope v1 与 legacy automation JSON 完全分离

- headless 输出不复用当前 `{"type":"log|event|result"}` 行结构。
- v1 envelope 的顶层字段至少包含：
  - `schema_version`
  - `ts`
  - `session_id`
  - `run_id`
  - `seq`
  - `event`
  - `data`
- `schema_version` 在 v1 中使用固定字符串，便于宿主在日志混流或升级期间可靠区分协议版本。

### Decision 4: Slice B 先覆盖最小事件集，不等待外部控制面

- 首批事件集至少覆盖：
  - `session.started`
  - `task.started`
  - `task.completed`
  - `task.failed`
  - `tool.invoke`
  - `tool.result`
  - `tool.error`
  - `approval.pending`
- `approval.resolved`、MCP 动态控制结果、capability handshake 等事件留到后续 Slice。

## Risks / Trade-offs

- [Risk] 先实现只读事件面，审批在 headless 下仍会失败。  
  → Mitigation: 用结构化错误把失败原因固定下来，避免宿主误判为 CLI 卡死。

- [Risk] 增加 `--headless` 可能与现有 `--output` 参数解析产生歧义。  
  → Mitigation: 明确参数互斥规则，并为错误组合添加测试。

- [Risk] 系统 Python 3.9 无法运行当前 `tests/unit/test_client_cli.py`。  
  → Mitigation: 在 feature evidence 中记录该基线阻塞，后续验证使用项目要求的 Python 版本或虚拟环境。

## Migration Plan

1. 增加 CLI 参数与模式分发，确保 headless 与 legacy 输出路径分离。
2. 实现 envelope v1 渲染与事件序列化。
3. 为 prompt suppression、legacy compatibility、approval error path 增加测试。
4. 更新 feature evidence、TODO ledger、OpenSpec tasks 状态。

## Open Questions

- `schema_version` 的字面值是否直接使用 `client-headless-event-envelope.v1`，还是与后续 control plane 共享更通用的命名空间？
- headless 下的终止错误是否需要单独的退出码，还是先复用现有非零退出码即可？
- 现有 event source 是否已经足够覆盖 `seq` / `run_id`，还是需要在 CLI 层额外补充投影逻辑？
