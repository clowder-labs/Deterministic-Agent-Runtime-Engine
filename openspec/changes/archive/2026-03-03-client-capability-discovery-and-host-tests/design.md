## Context

`client/` 在 Slice C 之后已经具备了可写的本地 control plane，但 capability discovery 仍然缺位：

- transport runtime 内部已经支持 `actions:list`，并返回当前注册的 canonical `resource:action` ids；
- CLI 宿主协议桥接目前只暴露 approvals / MCP / skills / status，未把 `actions:list` 暴露给外部宿主；
- 现有集成测试主要按功能面分段验证，还没有把 headless event envelope、control plane 和 capability discovery 作为统一协议面冻结。

Issue #135 的最后一片因此不需要再扩 transport 语义，而是要把已有 discovery surface 提升到 CLI 宿主协议面，并为协议稳定性建立联合回归。

## Goals / Non-Goals

**Goals:**

- 通过现有 `client-control-stdin.v1` 暴露显式 `actions:list` 能力发现。
- 明确 v1 discovery baseline：显式请求、结构化响应、无 startup handshake。
- 为宿主协议补齐 capability discovery happy path 与回归测试。
- 把 Slice D 的设计选择回写到 canonical docs 与 feature evidence。

**Non-Goals:**

- 本次不引入启动即发送的 capability handshake。
- 本次不为 action discovery 设计 richer metadata schema。
- 本次不引入新的控制通道（例如 loopback RPC / websocket）。
- 本次不改变 Slice B / Slice C 已落地的 envelope schema。

## Decisions

### Decision 1: v1 capability discovery 采用显式 `actions:list`

- 宿主通过已存在的 `--control-stdin` 通道显式发送 `actions:list`。
- CLI 不会在 session 启动时自动发送 discovery frame。
- 这一选择避免了在 headless event envelope 与 control result 多路复用流上再引入第三类“隐式 handshake”启动帧。

### Decision 2: discovery payload 继续复用 transport canonical shape

- `actions:list` 的返回结果继续使用现有 transport payload 形状：`{"actions": ["resource:action", ...]}`。
- 首版只承诺 canonical action id 列表，不额外附带 capability metadata。
- 返回动作必须与当前 session 真实可调用的 CLI host bridge surface 一致，而不是静态文档枚举。

### Decision 3: Slice D 把宿主协议作为联合回归面冻结

- 集成测试至少覆盖：
  - headless event envelope 基线仍可稳定输出；
  - `control-stdin` 在 `actions:list` 加入后不破坏现有 approvals / MCP / skills / status；
  - capability discovery 结果可被宿主直接消费，无需解析 help 文本或启动 chatter。
- 错误路径至少覆盖：
  - 不支持的 action 仍返回结构化错误；
  - 未请求 discovery 时不会出现 unsolicited startup handshake frame。

## Risks / Trade-offs

- [Risk] `actions:list` 可能暴露 runtime 内部尚未桥接的 action id。  
  → Mitigation: Slice D 需要明确 discovery 返回的是 CLI host bridge 当前 surface，而不是底层 transport 的全部潜在动作。

- [Risk] 把 startup handshake 推迟可能要求宿主多发一次 discovery 请求。  
  → Mitigation: 显式请求比隐式帧更容易做多路复用和兼容控制，首版优先稳定性而不是减少一个往返。

- [Risk] 回归测试过度绑定当前 action 列表，降低未来扩展空间。  
  → Mitigation: 测试以“至少包含 / error contract 稳定”为主，避免把列表顺序或未来扩展动作硬编码成脆弱断言。

## Migration Plan

1. 在 canonical docs 中把 Slice D 设计基线收敛到显式 `actions:list`，并明确 startup handshake 延后。
2. 在 CLI host bridge 中暴露 `actions:list`。
3. 增加 capability discovery 与宿主协议联合回归测试。
4. 回写 feature evidence、master TODO、review links 和最终归档记录。

## Open Questions

- `actions:list` 是否应只返回 action id 列表，还是需要在后续 slice 中增加 category / mutability / docs link 等 metadata？
