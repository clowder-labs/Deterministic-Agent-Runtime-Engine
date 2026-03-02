# AgentScope 迁移 Domain 执行清单（详细设计输入版，4人协同）

> 更新日期：2026-03-02  
> 输入基线：  
> - `docs/design/archive/agentscope-migration-framework-gaps.md`  
> - `examples/10-agentscope-compat-single-agent/DESIGN.md`  
> - `docs/todos/project_overall_todos.md`

## 0. 本轮约束与边界

- 不包含 Session 体系（并行开发中，不在本清单执行范围）。
- 当前阶段不要求历史兼容（允许直接调整接口，不做迁移层）。
- 不做 HITL 闭环；本轮关注完整权限模型与工具调用权限治理。
- `client send` 升级为：`content: string` + `uris: list` + `metadata`。
- `context.assemble` 负责把 `content + uris` 归一化为内部 message 结构。

## 0.1 认领声明（Claim Ledger）

> 用途：对本清单中的 TODO 先做执行声明，避免多人并行修改同一子域。  
> 规则：同一 TODO Scope 同时仅允许一个 `planned/active` 认领；到期需续期或释放。

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-20260302-D2D4 | D2-1~D2-4, D4-1~D4-4 | zts212653 | planned | 2026-03-02 | 2026-03-09 | `agentscope-d2-d4-thinking-transport` | 先处理 P0/P1 的 thinking 与 transport 协议统一。 |
| CLM-20260302-D5 | D5-1~D5-4 | zts212653 | planned | 2026-03-02 | 2026-03-09 | `agentscope-d5-safe-compression` | 压缩链路：tool pair safe + token-aware + auto trigger。 |
| CLM-20260302-D7 | D7-1~D7-4 | zts212653 | active | 2026-03-02 | 2026-03-09 | `agentscope-d7-plan-state-tools` | D7 实现与回归已完成，PR #138 待审。 |
| CLM-20260302-D1D3 | D1-1~D1-4, D3-1~D3-4 | zts212653 | planned | 2026-03-02 | 2026-03-09 | `agentscope-d1-d3-message-pipeline` | 多模态输入 schema 与 assemble normalize。 |

---

## 1. 能力/GAP 覆盖总览（用于确认“每个 TODO 支持什么能力”）

| AgentScope 能力 | 关键 Gap | 对应 Domain | 本轮目标能力补齐 |
|---|---|---|---|
| Msg / TextBlock | M1/M2/M3/M5 | D1 + D3 | 统一输入消息、内部消息块、URI 负载表达 |
| ChatModelBase | LM1/LM2/LM4 | D4 | thinking 内容保留、中间态可观测、usage 规范化 |
| ReActAgent | R5 + (部分 R1) | D4 + D5 | 自动压缩触发、执行中间态事件 |
| TruncatedFormatterBase | F1/F2/F4 | D5 | tool-pair-safe、token 级预算压缩、自动触发 |
| InMemoryMemory | Mem1/Mem2/Mem5 | D5 | 压缩行为安全与预算一致性 |
| Tool/Toolkit | T1 + 风险治理衍生 | D2 + D6 | tool_call/result 事件类型与权限 gate |
| PlanNoteBook / SubTask | P1/P2/P3 | D7 | plan 状态机、finish/revise 原生工具 |
| HttpStatefulClient（协议侧） | H1/H3（间接） | D2 | transport 消息类型与错误模型统一 |
| 全链路治理（项目级） | T2/T3/T5 | D6 + D8 | 权限判定、审计可追踪、日志规范化 |

说明：
- Session 相关 S1/S2/S3 本文不拆任务。
- 多模态完整链路以 D1+D3 为主，不要求本轮覆盖所有模型适配器原生多模态调用。

---

## 2. Domain 详细任务卡（含主要改动、支持能力、依赖）

## D1 `protocol/message`（输入协议与内部消息模型）

**主要改动**
- 新定义 `ClientSend` 输入协议（`content`, `uris`, `metadata`）。
- 新定义 `UriAttachment`（最小必须字段 + 可选 metadata）。
- 内部 `Message` 支持“文本 + 附件引用块”的统一表达（供 assemble 消费）。
- 明确输入约束：URI 数量/长度、metadata 大小、空文本处理。

**支撑能力**
- Msg/TextBlock 基础能力。
- 为多模态（图片/音频/视频）在协议层预留统一入口。

**建议改动位置**
- `dare_framework/transport/types.py`（客户端输入 envelope 相关类型）
- `dare_framework/context/types.py`（内部 message 结构）
- 新增协议 schema 文件（若项目采用独立 schema 模块）

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D1-1 | 定义 `ClientSend` | 新类型 + schema 校验 | Msg 输入标准化 | 无 | todo | 单测：合法/非法输入 |
| D1-2 | 定义 `UriAttachment` | URI 字段规范 + 校验 | 多模态入口 | 无 | todo | 单测：URI 错误码稳定 |
| D1-3 | 定义内部 `Message` 块结构 | message 内容块结构 | TextBlock/附件表达 | D1-1/2 | todo | assemble 可消费 |
| D1-4 | 约束与限制策略 | 限额/空值/超限错误模型 | 稳定输入治理 | D1-1/2/3 | todo | 压测与边界测试 |

---

## D2 `transport`（消息类型与payload协议）

**主要改动**
- 定义消息类型枚举：`message/tool_call/tool_result/thinking/error/status`。
- 统一 transport payload envelope 与错误模型。
- sender/receiver 对消息类型和错误码使用同一协议层定义。

**支撑能力**
- Tool/ChatModelBase 执行中间态传输。
- 后续 observability 的事件采集基础。

**建议改动位置**
- `dare_framework/transport/types.py`
- `dare_framework/transport/kernel.py`
- `dare_framework/transport/interaction/payloads.py`

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D2-1 | 定义消息类型枚举 | enum + 常量统一 | thinking/tool 事件标准化 | D1-1 | done | `tests/unit/test_transport_types.py` |
| D2-2 | 定义 payload 协议 | envelope schema + serializer | transport 语义一致 | D2-1 | done | `tests/unit/test_transport_adapters.py` |
| D2-3 | 错误码标准化 | error payload model | 可观测错误治理 | D2-2 | done | `tests/unit/test_transport_channel.py` |
| D2-4 | 协议测试矩阵 | e2e + contract test | 端到端稳定性 | D2-1/2/3 | done | `tests/unit/test_transport_types.py`, `tests/unit/test_transport_adapters.py` |

---

## D3 `context`（assemble 归一化与URI策略）

**主要改动**
- `assemble` 增加 `ClientSend -> Message` 归一化步骤。
- URI 解析策略：仅解析元信息 or 预取内容（本轮建议“元信息优先”）。
- 当模型不支持相关模态时，定义 deterministic 降级策略。

**支撑能力**
- Msg/TextBlock 到模型输入链路打通。
- 多模态输入处理策略集中化。

**建议改动位置**
- `dare_framework/context/context.py`
- `dare_framework/context/types.py`
- 可能新增 `context/attachment_resolver.py`

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D3-1 | 接入归一化管线 | assemble 前置 normalize | Msg 统一进入模型 | D1-3 + D2-2 | todo | 输入到模型链路测试 |
| D3-2 | URI 构建策略 | resolver + policy | 附件/富媒体引用处理 | D1-2 | todo | URI 成功/失败路径测试 |
| D3-3 | 降级策略 | text-only fallback 规则 | 多模型兼容执行 | D3-2 | todo | 不支持模态时行为稳定 |
| D3-4 | 组装链路回归 | context 集成测试 | 旧文本流程不回归 | D3-1/2/3 | todo | 回归全绿 |

---

## D4 `model + agent-loop`（thinking、usage、中间态）

**主要改动**
- `ModelResponse` 扩展 `thinking_content`（对应 Gap-LM1）。
- adapter usage 提取 `reasoning_tokens`（对应 Gap-LM4）。
- agent 执行循环通过 transport 发 `thinking/tool_call/tool_result` 事件。

**支撑能力**
- ChatModelBase thinking 保真。
- 执行过程可观测、可审计。

**建议改动位置**
- `dare_framework/model/types.py`
- `dare_framework/model/adapters/openai_adapter.py`
- `dare_framework/model/adapters/openrouter_adapter.py`
- `dare_framework/agent/react_agent.py`

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D4-1 | thinking_content | ModelResponse + adapter 提取 | ChatModelBase thinking | D2-1/2 | done | `tests/unit/test_openai_model_adapter.py`, `tests/unit/test_openrouter_adapter.py` |
| D4-2 | reasoning_tokens | usage parser 标准化 | 预算计量准确性 | D4-1 | done | `tests/unit/test_openai_model_adapter.py`, `tests/unit/test_openrouter_adapter.py` |
| D4-3 | 中间态事件 | loop 内发送 thinking/tool 事件 | 执行可观测 | D2-1/2/3 | done | `tests/unit/test_react_agent_gateway_injection.py` |
| D4-4 | 回归验证 | model+loop 集成测试 | 模型输出链路稳定 | D4-1/2/3 | done | `pytest -q`（528 passed, 12 skipped, 1 warning） |

---

## D5 `memory/compression`（安全压缩与预算收敛）

**主要改动**
- 压缩策略引入 tool pair safe（不孤儿化 call/result）。
- 增加 token 预算压缩策略（不仅消息条数）。
- 在调用模型前自动触发压缩（可按阈值配置）。

**支撑能力**
- TruncatedFormatterBase 关键行为。
- ReAct 长链路稳定性与上下文预算控制。

**建议改动位置**
- `dare_framework/compression/core.py`
- `dare_framework/context/context.py`（触发点）
- `dare_framework/agent/react_agent.py`（自动触发调用位）

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D5-1 | tool pair safe | compression 截断算法 | F1/Mem5 | D3-1 + D4-3 | done | `tests/unit/test_context_compression.py` |
| D5-2 | token 压缩 | token-aware 策略 | F2 | D4-2 | done | `tests/unit/test_context_compression.py` |
| D5-3 | 自动触发 | model 调用前压缩 hook | F4/R5 | D5-1/2 | done | `tests/unit/test_react_agent_gateway_injection.py` |
| D5-4 | 压缩矩阵测试 | truncate/summary/pair-safe | 压缩质量与稳定 | D5-1/2/3 | done | `pytest -q`（533 passed, 12 skipped, 1 warning） |

---

## D6 `security/permission`（权限与工具调用治理）

**主要改动**
- 定义权限模型：`subject/resource/action/decision/evidence`。
- ToolGateway 接入 policy gate，执行前统一判定。
- 将 tool risk/schema 与策略映射，形成默认 deny/allow 规则。
- 输出 allow/deny 审计证据，供日志和排障。

**支撑能力**
- 项目级权限治理（替代本轮 HITL 语义目标）。
- 工具调用可控、可审计。

**建议改动位置**
- `dare_framework/tool/tool_gateway.py`
- `dare_framework/tool/types.py`
- `dare_framework/security/*`（建议新增 domain）

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D6-1 | 权限模型定义 | policy types + evaluator 接口 | 统一判定语义 | D2-3 | todo | 模型/工具权限单测 |
| D6-2 | gateway gate 接入 | invoke 前策略判定 | 工具调用治理 | D6-1 | todo | 未授权 deterministic deny |
| D6-3 | 风险映射 | risk/schema -> policy rules | 风险分级治理 | D1-4 + D2-3 | todo | 高风险默认受限 |
| D6-4 | 审计证据输出 | decision log fields | 可追踪性 | D6-2/3 | todo | 证据字段稳定可查询 |

---

## D7 `plan`（状态机与原生工具补齐）

**主要改动**
- Step/Plan 状态机标准化（todo/in_progress/done/abandoned）。
- 原生补齐 `finish_plan` / `revise_current_plan`。
- critical_block 与计划状态联动更新。

**支撑能力**
- PlanNoteBook/SubTask 的框架原生能力（降低 compat shim 依赖）。

**建议改动位置**
- `dare_framework/plan_v2/types.py`
- `dare_framework/plan_v2/tools.py`
- `dare_framework/plan_v2/planner.py`

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D7-1 | 状态机 | Step/Plan 状态字段+迁移规则 | P1 | 无（独立） | done | `tests/unit/test_plan_v2_tools.py::test_plan_state_transition_rules_reject_terminal_reopen` |
| D7-2 | finish/revise 工具 | 新 plan tools + schema | P2/P3 | D7-1 | done | `tests/unit/test_plan_v2_tools.py::test_planner_exposes_revise_and_finish_plan_tools`，`tests/unit/test_plan_v2_tools.py::test_revise_current_plan_preserves_done_steps_by_step_id` |
| D7-3 | 状态提示联动 | critical_block 规则更新 | 执行引导一致性 | D7-1/2 | done | `tests/unit/test_plan_v2_tools.py::test_critical_block_requires_finish_when_all_steps_done` |
| D7-4 | 回归测试 | plan 全流程测试 | Plan 能力稳定 | D7-1/2/3 | done | `pytest -q tests/unit/test_plan_v2_tools.py tests/unit/test_react_agent_gateway_injection.py tests/unit/test_dare_agent_step_driven_mode.py`（31 passed）+ `pytest -q`（518 passed, 12 skipped, 1 warning） |

---

## D8 `observability`（日志与事件治理）

**主要改动**
- 统一日志字段：`trace_id/session_id/tool_call_id/message_type/policy_decision`。
- 接入 transport 事件日志与关键执行日志。
- 脱敏与采样策略标准化。

**支撑能力**
- 线上排障、联调追踪、权限判定回溯。

**建议改动位置**
- `dare_framework/observability/*`
- `dare_framework/transport/*`（事件发射点）
- `dare_framework/agent/react_agent.py`（执行链路关键日志）

| ID | 任务 | 主要代码改动 | 支持能力 | 依赖 | 状态 | 输出证据 |
|---|---|---|---|---|---|---|
| D8-1 | 日志字段规范 | logging schema + helper | 全链路一致日志 | D2-1/2 | todo | 字段一致性检查 |
| D8-2 | transport 事件日志 | 事件落日志/trace | 中间态可检索 | D4-3 + D6-4 | todo | thinking/tool 事件可查 |
| D8-3 | 脱敏/采样策略 | scrub + sampling | 安全与成本平衡 | D8-1 | todo | 敏感字段不泄漏 |
| D8-4 | 覆盖检查脚本 | 校验脚本 | 治理闭环 | D8-1/2/3 | todo | 检查脚本可发现漏点 |

---

## 3. 任务间兼容性矩阵（重点：不是历史兼容，而是“并行开发接口兼容”）

| 接口项 | 生产方 | 消费方 | 冲突风险 | 冻结时点 |
|---|---|---|---|---|
| `ClientSend` schema | D1 | D3/D2 | 字段名变动导致 assemble/transport 断裂 | Gate-1 |
| `Message` 内容块结构 | D1/D3 | D4/D5 | 模型输入与压缩算法理解不一致 | Gate-2 |
| transport 消息类型枚举 | D2 | D4/D8/CLI | 事件类型命名漂移 | Gate-1 |
| tool_call/tool_result payload 结构 | D2 | D4/D5/D8 | tool pair 匹配失败 | Gate-2 |
| 错误码模型 | D2 | D6/D8 | deny/error 无法统一观测 | Gate-3 |
| policy decision 结构 | D6 | D8 | 审计日志字段不一致 | Gate-3 |
| plan 状态字段语义 | D7 | D4(执行提示) | 状态迁移语义冲突 | Gate-3 |

---

## 4. 强依赖关系

1. `D1 -> D2 -> D3`（先统一协议，再接 assemble）。
2. `D2 -> D4 -> D8`（先有事件类型，再发中间态，再观测）。
3. `D3 -> D5`（压缩策略依赖统一 message 结构）。
4. `D2 + D1约束 -> D6`（权限动作与风险映射依赖稳定 schema）。
5. `D7` 可并行，仅在权限接入点弱依赖 `D6`。

---

## 5. 四人并行分工（基于依赖最小阻塞）

| 人员 | 主责 | 第一阶段产出 | 第二阶段产出 |
|---|---|---|---|
| Dev-A | D1 + D2 + D3 | Gate-1：`ClientSend` + transport 类型冻结 | Gate-2：assemble 归一化冻结 |
| Dev-B | D6 | Gate-3：policy gate + decision 结构冻结 | 权限审计证据落地 |
| Dev-C | D7 | plan 状态机 + finish/revise 工具 | plan 全流程回归 |
| Dev-D | D4 + D5 + D8 | thinking/usage + 压缩策略实现 | 事件观测与全链路联调 |

---

## 6. 交接 Gate 定义

1. **Gate-1（协议冻结）**  
   冻结：`ClientSend`、`UriAttachment`、transport 消息类型枚举、错误码主集合。  
2. **Gate-2（组装冻结）**  
   冻结：`assemble` 归一化输入输出结构、tool 事件 payload 结构。  
3. **Gate-3（治理冻结）**  
   冻结：policy decision 结构、plan 状态字段语义、日志主字段键。  
4. **Gate-4（联调验收）**  
   `client send -> assemble -> model/tool loop -> policy gate -> transport -> logs` 全链路通过。

---

## 7. 联调验收（跨域）

- `ClientSend(content+uris)` 能稳定进入模型调用链路。
- transport 连续输出 `thinking -> tool_call -> tool_result -> final message`。
- 未授权工具被 deterministic 拒绝，且有可检索审计证据。
- 压缩不破坏 tool pair，且预算超限自动触发。
- plan 原生工具覆盖 create/revise/finish 主流程，无 compat shim 依赖。
