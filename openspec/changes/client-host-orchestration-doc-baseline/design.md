## Context

当前 `client/` 已经具备：

- `run/script` 非交互执行入口；
- `--output json` 的自动化行输出；
- `skills list` 与 `mcp list/inspect/reload/unload`；
- framework 内部已有 `actions:list`、`approvals:*`、`mcp:*`、`skills:list` 等 deterministic action 基础。

但这些能力仍未被整理成“宿主托管协议”。本 change 不实现协议，只把后续实现需要遵守的设计边界、兼容策略和 TODO slice 固化下来。

## Goals / Non-Goals

**Goals:**

- 为 `client` 建立宿主编排的 canonical 设计基线。
- 明确当前 automation-json 与未来 headless contract 的边界。
- 为后续 Slice B/C/D 提供稳定的 capability 约束与 TODO 映射。
- 保持仓库 docs-first 工作流完整：Claim Ledger、OpenSpec、feature evidence、intent PR payload 一致。

**Non-Goals:**

- 本次不修改 `client` 运行时行为。
- 本次不实现 `--headless`、`--control-stdin` 或新的事件 schema。
- 本次不为外部宿主定义远程网络控制协议。

## Decisions

### Decision 1: 现有 `--output json` 保留为 legacy automation schema

- 当前 `log/event/result` 行结构继续保留，避免破坏现有脚本与测试。
- 新的宿主协议不得直接复用这三类行结构，而应显式使用 versioned envelope。
- 文档层必须明确两者边界，避免调用方误判。

### Decision 2: headless host orchestration 作为独立模式，而不是 `chat/run/script` 的隐式变体

- interactive 允许 `dare>` prompt 与内联审批；
- automation-json 允许脚本消费 JSON 行；
- headless 只允许结构化事件流与结构化控制面。

理由：只有显式模式切换，宿主才能依赖“禁止人类交互副作用”的强语义。

### Decision 3: v1 外部控制面优先选 `control-stdin`

- `control-stdin` 避免新增本地端口、发现机制与额外鉴权面。
- 行级 JSON 帧足以覆盖 approvals / MCP / skills / actions / status 基线控制。
- loopback RPC 可作为未来增强，但不进入当前设计承诺。

### Decision 4: capability discovery 是宿主协议的基线能力，不是附属优化

- `actions.list` 或等价启动握手必须进入宿主协议设计。
- 宿主不能依赖硬编码支持矩阵来判断某个 `client` 版本是否支持某 action。

### Decision 5: docs baseline 必须落在多层文档，而不是只改一个局部 README

- `client/DESIGN.md` 负责详细设计；
- `client/README.md` 负责用户可见边界；
- `docs/design/modules/event/README.md` 与 `docs/design/TODO_INDEX.md` 负责 canonical backlog 与跨模块追踪；
- `docs/features/<change-id>.md` 负责 Slice A 的状态与证据。

## Risks / Trade-offs

- [Risk] 先写未来协议设计，短期会形成“文档先于实现”的差距。  
  → Mitigation: 明确标注 `planned`，并把 Slice B/C/D 绑定到同一 master TODO。

- [Risk] 继续保留 legacy automation schema 会增加双轨维护成本。  
  → Mitigation: 明确 legacy 与 headless 的分层语义，避免后续再混为一谈。

- [Risk] `control-stdin` 可能不足以覆盖未来复杂宿主场景。  
  → Mitigation: 将 loopback RPC 保留为后续可扩展方向，但不影响 v1 最小能力落地。

## Migration Plan

1. Slice A：建立 docs baseline、OpenSpec capability、feature evidence、intent PR payload。
2. Slice B：实现 `--headless` 与 versioned event envelope v1。
3. Slice C：实现 `--control-stdin` 与 approvals / MCP / skills 的外部控制。
4. Slice D：实现 capability discovery 与宿主协议回归测试。

Rollback:

- 若团队否决该设计方向，可回退本 change 的设计文档与 capability 定义，恢复到“仅支持 automation-json”的当前表述。

## Open Questions

- `status.show` 是否需要作为独立 action，还是由 `actions.list` + 事件流已足够？
- `session.started` 是否承担完整握手，还是需要单独的 capability handshake 事件？
- 宿主协议 envelope 是否应直接复用 transport `seq/stream_id` 命名，还是在 CLI 层做字段投影？
