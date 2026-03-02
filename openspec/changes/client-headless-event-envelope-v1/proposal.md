## Why

Slice A 的 docs-only 基线已经通过 PR `#141` 合入 `main`，Issue #135 的下一步不再是补文档边界，而是把 `client/` 的“可脚本化调用”推进到“可被宿主稳定接入”的第一段实现能力。

当前 `main` 仍然缺少两项 Slice B 的阻塞能力：

1. 没有显式的 headless 模式，`run/script` 仍可能落回 prompt 或内联审批语义。
2. 当前 `--output json` 仍是 legacy automation schema，缺少宿主协议需要的 versioned envelope 与关联字段。

如果直接跳到外部 control plane 或 capability discovery，宿主仍然拿不到稳定的只读事件流，也无法确认 CLI 何时会掉回人类交互路径。因此 Slice B 先收敛到“显式 headless + versioned event envelope v1”。

## What Changes

- 为 `client run` / `client script` 引入显式 `--headless` 模式边界。
- 在 headless 模式下禁止 `dare>` prompt 与内联审批输入，改为结构化事件和结构化终止错误。
- 新增与 legacy automation JSON 分离的 event envelope v1，包含稳定的版本号、关联字段与事件类型。
- 为 headless 模式与 envelope v1 增加测试，覆盖 happy path 和 changed error branch。

## Capabilities

### Modified Capabilities

- `client-host-orchestration`: 将 Slice A 的设计约束落实为可执行的 headless mode 与 event envelope v1。
- `transport-channel`: 为 CLI 宿主事件流补充版本化、关联语义与非交互错误路径约束。

## Impact

- 影响文件：
  - `client/main.py`
  - `client/render/json.py`
  - `client/runtime/event_stream.py`
  - `tests/unit/test_client_cli.py`
  - `tests/integration/test_client_cli_flow.py`
  - `docs/features/client-headless-event-envelope-v1.md`
  - `openspec/changes/client-headless-event-envelope-v1/**`
- 不包含：
  - 外部 `control-stdin` / loopback RPC
  - capability discovery 握手
  - MCP 外部控制实现
