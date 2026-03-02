---
change_ids: []
doc_kind: analysis
topics: ["client-cli", "host-orchestration", "issue-135", "headless-protocol"]
created: 2026-03-02
updated: 2026-03-02
status: active
mode: openspec
---

# 2026-03-02 DARE Client CLI 宿主编排 Gap Analysis（Issue #135）

> 类型：专题 gap 分析
> 范围：`/client` 作为“可被外部宿主稳定编排的 CLI agent”时的协议与控制面差距
> 关联 issue：GitHub `#135`
> 评审基线：当前仓库 `client/` 实现、`client/DESIGN.md`、`client/README.md`、相关测试与 transport action/event 契约

---

## 1. 先纠偏（避免错误范围）

本议题的真实入口是 `client/`，不是 `examples/06-dare-coding-agent-mcp/cli.py`。

当前 `client/` 已具备的能力：

1. 非交互执行路径已经存在：
   - `client/main.py` 提供 `run` / `script` 子命令。
2. 结构化输出已经存在：
   - `client/main.py` 提供 `--output human|json`。
   - `client/README.md` 已定义 `log/event/result` 三类 JSON 行。
3. Skills 与动态 MCP 能力已经暴露：
   - `client/main.py` 提供 `skills list`、`mcp list/inspect/reload/unload`。
   - `client/commands/mcp.py` 已接运行时 `reload_mcp/unload_mcp`。
4. framework 内部已有可复用的 transport envelope 元数据：
   - `dare_framework/transport/types.py` 已定义 `event_type`、`stream_id`、`seq`。

因此，本议题不是“补齐从无到有的 CLI 基础能力”，而是把现有 `client/` 从“可脚本化调用”提升到“可被宿主稳定托管”的协议级能力。

---

## 2. 当前结论

- `client/` 已经是 **L1 可接入候选**。
- 真实 gap 集中在 **协议硬边界、外部控制通道、事件 envelope 稳定性、能力发现、宿主级测试**。
- 根据文档先行治理要求，这一轮应先补 **设计事实源 + master TODO**，再按切片进入 OpenSpec 与实现。

---

## 3. Gap 明细

| Gap ID | 设计声明（Design Claim） | 代码现状（Code Evidence） | 影响评估（Impact） | 建议动作（Action） | 优先级 |
|---|---|---|---|---|---|
| CCLI-GAP-001 | `client/` 需要有显式、可依赖的 headless 合约，保证宿主可强约束其只走结构化 I/O。 | `client/main.py` 仍以 `chat` + `input("dare> ")` 作为交互主循环；parser 只有 `--output human|json`，没有 `--headless` 或等价语义开关。`client/DESIGN.md` 只定义交互与 JSON 输出模式。 | 宿主虽然可以调用 `run/script`，但无法依赖一套“禁止 prompt / 禁止内联审批 / 禁止人类文案漂移”的强语义模式。 | 在设计文档中定义 `interactive` 与 `headless` 的模式边界、禁止行为、退出码与审批语义；后续实现显式开关。 | P1 |
| CCLI-GAP-002 | 机器可读输出需要宿主稳定字段与版本化 envelope，而不只是展示型 JSON。 | `client/main.py` 当前 JSON 输出为 `{"type":"log|event|result", ...}`；`client/README.md` 也只声明这三类结构；`tests/unit/test_client_cli.py` 直接锁定该简化 schema。 | 缺少 `schema_version`、`run_id`、`seq`、关联字段时，宿主难以做跨版本兼容、幂等重放、事件关联和细粒度生命周期解析。 | 先在设计层定义 `headless event envelope v1`，明确与现有 `--output json` 的兼容策略，再切实现。 | P1 |
| CCLI-GAP-003 | 宿主应能在活跃执行期间持续下发结构化控制，而不是仅限同进程 transport 调用。 | `client/runtime/action_client.py` 的 action/control 仅封装 `DirectClientChannel.ask(...)`；CLI 参数层没有 `--control-stdin`、`--control-port` 等宿主可接入控制面。 | 外部平台难以对运行中的任务执行审批、MCP 热重载、skills 查询、状态轮询等持续控制。 | 先定义外部 control plane（例如 `stdin` JSON 帧或 loopback RPC）的协议、动作集合、鉴权和错误语义。 | P1 |
| CCLI-GAP-004 | CLI 应向宿主暴露“能力发现”协议面，避免外部系统硬编码支持矩阵。 | framework 内部已有 `actions:list` 枚举，但 CLI 对外仅提供 `tools/skills/config/model/mcp/approvals/control` 等命令，没有 `actions list` 或等价启动握手。 | 宿主在对接时只能预设 CLI 能力，无法做启动协商或按能力降级。 | 将 `actions:list` 提升到 CLI 宿主协议面，并在设计中定义启动能力声明或显式查询命令。 | P2 |
| CCLI-GAP-005 | 动态 MCP 需要补齐“宿主实时注入”闭环，而不只是会话内命令能力。 | `client/commands/mcp.py` 已支持 `reload/unload`，但仍依附当前进程 runtime；缺少外部控制协议将其绑定到活跃 run。 | 现有能力更像“人工 / 单脚本可用”，不是“外部平台实时编排可用”。 | 将 `mcp:list/reload/unload/show-tool` 纳入外部 control plane，并明确运行中可见性与一致性语义。 | P2 |
| CCLI-GAP-006 | 宿主编排能力需要设计级与测试级双重基线，确保后续演进不回退。 | `client/DESIGN.md` 尚未定义宿主编排协议；现有测试覆盖 `--output json`、审批超时、CLI 基础路径，但没有 headless 协议稳定性、外部控制、能力发现集成测试。 | 即使后续补实现，也容易因为缺少设计锚点与回归测试而再次漂移。 | 先更新 canonical 设计文档，再增加协议级集成测试清单作为 slice 验收入口。 | P0 |

---

## 4. 影响范围

### 4.1 设计与文档

- `client/DESIGN.md`
- `client/README.md`
- `docs/design/TODO_INDEX.md`
- 视切片范围补充到 `docs/design/modules/event/README.md` 或相关 transport / interaction 设计文档

### 4.2 实现

- `client/main.py`
- `client/runtime/action_client.py`
- `client/runtime/event_stream.py`
- `client/render/json.py`
- 可能涉及 `dare_framework/transport/**` 与 interaction dispatcher 适配层

### 4.3 测试

- `tests/unit/test_client_cli.py`
- `tests/integration/test_client_cli_flow.py`
- 新增宿主协议集成测试（headless / control / capability discovery）

---

## 5. 建议切片（供 master TODO / OpenSpec 使用）

1. Slice A: 设计基线更新
   - 目标：把 `client` 宿主编排协议写成 canonical docs。
2. Slice B: headless 模式与事件 envelope v1
   - 目标：定义并实现稳定宿主事件流。
3. Slice C: 外部 control plane v1
   - 目标：让宿主可在运行中持续控制审批 / MCP / skills。
4. Slice D: capability discovery + 协议级测试
   - 目标：完成能力握手与回归基线。

---

## 6. 风险提示

1. 直接修改现有 `--output json` 语义会打破现有 README 与测试契约，必须先定义兼容策略。
2. 若先做代码、后补设计，后续 OpenSpec 切片边界会混乱，不符合仓库 SOP。
3. 若只补事件输出而不补外部控制面，CLI 仍然只能算“可观察”，不能算“可托管”。

---

## 7. 本轮结论

- Issue #135 应继续推进，但目标应重写为：
  - “补齐 `client/` 的宿主编排协议能力”
  - 而不是“回到 examples CLI 重做一套”
- 下一步应创建对应 master TODO，并将以上 6 个 gap 映射到可独立执行的 slice。
