## Why

Slice B 已经把 `client/` 推进到显式 headless + versioned event envelope v1，但宿主仍然只能“看”事件，不能对活跃 run 发回结构化控制。Issue #135 的下一段缺口因此不在事件读取，而在本地 control plane。

当前 `main` 的阻塞点有两类：

1. 审批、MCP、skills 与 session status 仍主要暴露为 CLI 内部 slash 命令或 `TransportActionClient` 直接调用，宿主没有外部稳定入口。
2. `client/` 还没有定义控制命令帧、结果帧、错误帧和运行中生效语义，导致 headless 会话只能 fail-fast，不能被宿主接管。

Slice C 先收敛到 `--control-stdin` 这一条本地控制面：避免提前引入 loopback 端口和身份边界，同时复用已有 canonical action ids 与现有运行时语义。

## What Changes

- 为 `client run` / `client script` 的 headless 会话引入 `--control-stdin` 控制面入口。
- 定义 control command/result/error envelope v1，明确 `schema_version`、请求关联 `id`、`action`、`params`、`ok`、`result`、`error` 字段。
- 将 approvals、MCP、skills 与 status 的最小控制面桥接到外部宿主协议。
- 为控制往返、错误路径和运行中生效语义增加测试与执行证据。

## Capabilities

### Modified Capabilities

- `client-host-orchestration`: 把“planned control plane”推进为首个 landed 外部控制入口。
- `transport-channel`: 复用 canonical `resource:action` 语义作为 CLI 控制桥接目标，而不是引入新的 dotted 命名。

## Impact

- 影响文件：
  - `client/main.py`
  - `client/runtime/action_client.py`
  - `client/commands/mcp.py`
  - `tests/unit/test_client_cli.py`
  - `tests/integration/test_client_cli_flow.py`
  - `docs/features/client-external-control-plane-v1.md`
  - `openspec/changes/client-external-control-plane-v1/**`
- 不包含：
  - loopback RPC / `--control-port`
  - capability discovery 握手
  - `mcp:unload` canonicalization
