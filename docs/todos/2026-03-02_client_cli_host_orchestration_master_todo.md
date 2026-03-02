---
change_ids: []
doc_kind: todo
topics: ["client-cli", "host-orchestration", "issue-135", "headless-protocol"]
created: 2026-03-02
updated: 2026-03-02
status: active
mode: openspec
---

# 2026-03-02 Client CLI 宿主编排 Master TODO（Issue #135）

> 来源：`docs/todos/2026-03-02_client_cli_host_orchestration_gap_analysis.md`
> 执行模型：docs baseline -> OpenSpec slice -> docs-only intent PR -> implementation -> evidence -> archive
> 范围：仅覆盖 `client/` 作为外部宿主可编排 CLI 的协议与治理闭环

## 认领声明（Claim Ledger）

> 当前状态：Slice A / Slice B 已于 2026-03-02 完成并合入 `main`，当前进入 Slice C kickoff。
> Slice C 负责外部 control plane v1；Slice D 继续承担 capability discovery 与宿主级回归测试。

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-20260302-CCLI-A | CCLI-001~CCLI-002 | bouillipx | done | 2026-03-02 | 2026-03-09 | `client-host-orchestration-doc-baseline` | Slice A: docs baseline 已随 PR `#141` 合入 `main`，待归档到 `openspec/changes/archive/2026-03-02-client-host-orchestration-doc-baseline/`。 |
| CLM-20260302-CCLI-B | CCLI-003~CCLI-004 | bouillipx | done | 2026-03-02 | 2026-03-09 | `client-headless-event-envelope-v1` | Slice B: headless event envelope v1 已随 PR `#145` 合入 `main`，待归档到 `openspec/changes/archive/2026-03-02-client-headless-event-envelope-v1/`。 |
| CLM-20260302-CCLI-C | CCLI-005~CCLI-006 | bouillipx | active | 2026-03-02 | 2026-03-09 | `client-external-control-plane-v1` | Slice C: 建立 `--control-stdin` v1 基线、MCP/approval/status/skills 外部控制 contract 与 docs-only intent PR payload。 |

## 切片规划

| Slice | 目标 | 建议 OpenSpec Change | 主要覆盖 TODO |
|---|---|---|---|
| Slice A | 更新 canonical 设计与 README，明确宿主编排 contract | `client-host-orchestration-doc-baseline` | CCLI-001, CCLI-002 |
| Slice B | 定义并实现 headless 模式与事件 envelope v1 | `client-headless-event-envelope-v1` | CCLI-003, CCLI-004 |
| Slice C | 定义并实现外部 control plane v1 | `client-external-control-plane-v1` | CCLI-005, CCLI-006 |
| Slice D | 暴露 capability discovery，并补齐宿主协议回归测试 | `client-capability-discovery-and-host-tests` | CCLI-007, CCLI-008 |

## TODO 清单

| ID | Priority | Status | Gap ID | Planned OpenSpec Change | Task | Owner | Evidence | Last Updated |
|---|---|---|---|---|---|---|---|---|
| CCLI-001 | P0 | done | CCLI-GAP-006 | `client-host-orchestration-doc-baseline` | 更新 `client/DESIGN.md`，新增“宿主编排 / headless / control plane / capability discovery / 错误语义”章节，作为后续实现唯一设计输入。 | bouillipx | `client/DESIGN.md`；`openspec/changes/archive/2026-03-02-client-host-orchestration-doc-baseline/` | 2026-03-02 |
| CCLI-002 | P0 | done | CCLI-GAP-006 | `client-host-orchestration-doc-baseline` | 更新 `client/README.md`，明确当前 `--output json` 是 legacy automation schema，补充后续宿主协议模式的兼容说明。 | bouillipx | `client/README.md`；`docs/features/archive/client-host-orchestration-doc-baseline.md` | 2026-03-02 |
| CCLI-003 | P1 | done | CCLI-GAP-001 | `client-headless-event-envelope-v1` | 为 `client` 设计并实现显式 headless 模式，定义禁止 prompt / 禁止内联审批 / 只输出协议帧的行为边界。 | bouillipx | `client/main.py`；`client/session.py`；`tests/integration/test_client_cli_flow.py`；`docs/features/archive/client-headless-event-envelope-v1.md` | 2026-03-02 |
| CCLI-004 | P1 | done | CCLI-GAP-002 | `client-headless-event-envelope-v1` | 设计并实现 versioned event envelope（至少含 `schema_version`、`run_id`、`seq`、`event`、`data`），并定义与现有 JSON 输出的兼容策略。 | bouillipx | `client/render/headless.py`；`tests/unit/test_client_cli.py`；`tests/integration/test_client_cli_flow.py`；`docs/features/archive/client-headless-event-envelope-v1.md` | 2026-03-02 |
| CCLI-005 | P1 | todo | CCLI-GAP-003 | `client-external-control-plane-v1` | 设计外部控制协议入口（如 `control-stdin` 或 loopback RPC），覆盖 approvals / MCP / skills / status 的结构化控制。 | bouillipx | `client/main.py`；`client/runtime/action_client.py`；相关 OpenSpec design/specs/tasks | 2026-03-02 |
| CCLI-006 | P2 | todo | CCLI-GAP-005 | `client-external-control-plane-v1` | 将当前 canonical MCP actions（首批为 `mcp:list/reload/show-tool`）接入外部 control plane，并明确运行中生效与错误处理语义。CLI 层 `unload` 待后续补 canonical action 后再纳入宿主协议面。 | bouillipx | `client/commands/mcp.py`；相关集成测试 | 2026-03-02 |
| CCLI-007 | P2 | todo | CCLI-GAP-004 | `client-capability-discovery-and-host-tests` | 将 `actions:list` 提升到 CLI 宿主协议面，并定义启动握手或显式查询命令。 | TBD | `dare_framework/transport/interaction/resource_action.py`；`client/main.py`；相关文档 | 2026-03-02 |
| CCLI-008 | P1 | todo | CCLI-GAP-006 | `client-capability-discovery-and-host-tests` | 新增 headless 协议稳定性、外部控制、能力发现三组集成测试，并回写 README / 设计文档中的验证锚点。 | TBD | `tests/integration/test_client_cli_flow.py`；新增协议测试文件 | 2026-03-02 |

---

## 执行规则

1. 不允许直接从 CCLI-003 开始写代码；必须先完成 CCLI-001 / CCLI-002 并提交 docs-only intent PR。
2. 每个 OpenSpec change 只消费上表中的一个 slice，不混切多个高风险协议面。
3. 任何会改变现有 `--output json` 行格式的方案，都必须先写清兼容策略与迁移说明。
4. `Claim Ledger`、OpenSpec `tasks.md`、后续 `docs/features/<change-id>.md` 必须对齐同一组 TODO IDs。

## 建议验收边界

### Slice A

- `client/DESIGN.md` 已能独立描述宿主编排 contract。
- `client/README.md` 已说明 legacy JSON 与未来宿主协议面的边界。

### Slice B

- headless 模式下不存在 `dare>` prompt 或内联审批提示。
- 宿主可稳定解析事件 envelope，且 error path 也有一致 schema。

### Slice C

- 宿主可对活跃 run 下发至少一类审批指令与一类 MCP 指令。
- control plane 错误语义可结构化返回，而非仅 stdout 文案。

### Slice D

- 宿主可查询能力清单，而非硬编码支持矩阵。
- 回归测试可覆盖 happy path 与 changed error path。
