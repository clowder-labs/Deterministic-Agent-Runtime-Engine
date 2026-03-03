## Why

Slice C 已经让宿主可以通过 `--control-stdin` 对活跃 headless run 发送 approvals / MCP / skills / status 控制，但宿主仍然必须硬编码“当前 CLI 支持哪些动作”。Issue #135 剩余的协议缺口因此不再是控制写路径，而是显式能力发现与宿主级回归冻结。

当前 `main` 的剩余问题有两类：

1. CLI 宿主协议面还没有暴露 `actions:list`，宿主无法在运行时查询当前 session 的 canonical action surface。
2. headless event envelope、control-stdin 和 capability discovery 还没有被同一组宿主协议回归测试一起冻结，后续演进容易在一个面上修复时回退另一个面。

Slice D 收敛到两件事：把 `actions:list` 提升为宿主协议动作，并补齐宿主级协议回归测试。启动即发送的 capability handshake 不纳入这一版基线，避免在 stdout 多路复用流里额外引入隐式协议帧。

## What Changes

- 为 `run/script --headless --control-stdin` 暴露显式 `actions:list` capability discovery。
- 定义 Slice D 的 v1 discovery baseline：显式请求、结构化返回、无 unsolicited startup handshake。
- 增加宿主协议集成测试，覆盖 headless event envelope、control plane 和 capability discovery 的联合回归面。
- 回写 `client/DESIGN.md`、`client/README.md`、master TODO 和 feature evidence，作为实现前的 docs-first 基线。

## Capabilities

### Modified Capabilities

- `client-host-orchestration`: 把“planned capability discovery”推进为显式 `actions:list` 宿主协议动作，并补齐协议回归锚点。

## Impact

- 影响文件：
  - `client/main.py`
  - `client/DESIGN.md`
  - `client/README.md`
  - `tests/unit/test_client_cli.py`
  - `tests/integration/test_client_cli_flow.py`
  - `docs/todos/2026-03-02_client_cli_host_orchestration_master_todo.md`
  - `docs/features/client-capability-discovery-and-host-tests.md`
  - `openspec/changes/client-capability-discovery-and-host-tests/**`
- 不包含：
  - 启动即发送的 capability handshake
  - 更丰富的 capability metadata schema（标签、权限、分类矩阵）
  - 新的网络控制入口或 `--control-port`
