# DARE 对外 CLI 详细设计（`client/`）

## 1. 背景与目标

当前仓库已有多个示例 CLI（`examples/04`、`examples/05`、`examples/06`、`examples/10`），但它们面向示例场景，存在以下问题：

1. 功能分散在示例目录，外部用户没有统一入口。
2. 命令能力不统一（审批、MCP、transport action、脚本执行分布不一致）。
3. 复用较多示例级实现，缺少可维护的产品化模块边界。

本设计目标：在仓库根目录新增 `client/`，提供一个“可对外、可长期维护”的统一 CLI。

## 2. 设计范围

### 2.1 In Scope（一期必须）

1. 提供统一命令入口（交互 + 非交互）。
2. 支持任务执行（直接执行 / 计划预览后审批执行）。
3. 支持工具审批全流程（list/poll/grant/deny/revoke）。
4. 支持 MCP 管理（list/inspect/reload/unload）。
5. 支持配置、模型、工具、技能信息查询。
6. 支持脚本模式（用于演示/CI）。
7. 提供稳定的退出码与结构化输出（human/json）。

### 2.2 Out of Scope（一期不做）

1. Web UI / TUI 图形界面。
2. 远程多节点编排与分布式队列。
3. 新增框架核心能力（仅复用现有 `dare_framework`）。

### 2.3 宿主编排协议基线（planned）

Issue #135 之后，`client/` 还需要补一层“宿主可稳定托管”的协议面，但该能力当前仍处于规划态。

本轮设计基线约束：

1. **不回退当前 CLI 可用性**：`chat/run/script` 与现有 `--output json` 行为保持兼容。
2. **显式区分三类模式**：
   - interactive（当前主路径，已落地）
   - automation-json（当前脚本集成路径，已落地但仅是 legacy automation schema）
   - headless host orchestration（Slice B 已落地最小事件面）
3. **后续变更必须以显式协议切面落地**，不能继续把宿主编排能力混在 `dare>` prompt、内联审批和展示型 JSON 输出中。

## 3. 总体方案

### 3.1 关键决策

1. **CLI 解析库使用 `argparse`**：保持零新增核心依赖，与现有示例一致。
2. **执行与控制解耦**：
   - 任务执行使用 `agent(Message(...), transport=channel)`；对话级元数据（如 `conversation_id`）进入 `Message.metadata`。
   - 查询/控制统一走 transport action/control（`approvals:*`、`mcp:*`、`config:get` 等）。
3. **单进程内 transport 适配**：
   - 使用 `DirectClientChannel + AgentChannel.build(...)`，确保 action/control 协议一致。
4. **默认安全策略**：
   - 高风险工具审批默认开启（复用 `ToolApprovalManager` 默认行为）。
   - 不提供默认绕过审批的开关。
5. **宿主协议与现有 JSON 输出分层**：
   - 当前 `--output json` 继续作为脚本/调试输出层。
   - 规划中的宿主编排协议使用独立 headless contract，避免与现有 JSON 行格式耦合。
6. **v1 外部控制面优先使用本地 stdin 命令帧**：
   - 相比本地 HTTP/JSON-RPC，`control-stdin` 不新增端口、鉴权面与进程发现复杂度，更适合作为最小宿主协议基线。

### 3.2 架构图

```text
┌──────────────────────────┐
│        CLI Frontend      │
│ argparse + repl parser   │
└─────────────┬────────────┘
              │
┌─────────────▼────────────┐
│      Client Runtime      │
│ Session + Task Runner    │
│ Action/Control Client    │
│ Event Pump + Renderer    │
└─────────────┬────────────┘
              │
┌─────────────▼────────────┐
│   dare_framework Agent   │
│ DareAgentBuilder/build   │
│ DirectClientChannel      │
│ AgentChannel (action)    │
└──────────────────────────┘
```

## 4. `client/` 目录结构

```text
client/
├── __init__.py
├── __main__.py                 # python -m client
├── main.py                     # 顶层 argv -> subcommand dispatch（含 chat/run/script 主路径）
├── README.md                   # 使用说明与退出码约定
├── session.py                  # CLISessionState / ExecutionMode / SessionStatus
├── session_store.py            # workspace 级 session snapshot 持久化与恢复
├── parser/
│   ├── command.py              # 交互命令解析（/mode /approve ...）
│   └── kv.py                   # key=value 参数解析
├── runtime/
│   ├── bootstrap.py            # 构建 agent + channel + client
│   ├── task_runner.py          # run/plan-preview/background-task
│   ├── action_client.py        # action/control 请求封装
│   └── event_stream.py         # unsolicited transport 消息消费
├── commands/
│   ├── approvals.py
│   ├── info.py                 # tools/skills/config/model/doctor/control 查询与控制
│   ├── mcp.py
└── render/
    ├── human.py
    └── json.py
```

## 5. 命令面设计

### 5.1 顶层命令树

```text
dare chat [--resume [session-id|latest]] [--session-id <session-id>] [options]
dare run --task "..." [--resume [session-id|latest]] [--session-id <session-id>]
dare script --file demo.txt [--resume [session-id|latest]] [--session-id <session-id>]
dare sessions list

dare approvals list
dare approvals poll [--timeout-ms 30000]
dare approvals grant <request_id> [--scope workspace] [--matcher exact_params] [--matcher-value ...] [--session-id ...]
dare approvals deny  <request_id> [--scope once]      [--matcher exact_params] [--matcher-value ...] [--session-id ...]
dare approvals revoke <rule_id>

dare mcp list
dare mcp inspect [tool_name]
dare mcp reload [paths...]
dare mcp unload

dare tools list
dare skills list
dare config show
dare model show
dare control <interrupt|pause|retry|reverse>
dare doctor
```

### 5.2 交互模式（`dare chat`）内命令

1. `/mode plan|execute`
2. `/approve`、`/reject`
3. `/status`
4. `/approvals ...`
5. `/mcp ...`
6. `/tools list`、`/skills list`、`/config show`、`/model show`
7. `/interrupt`
8. `/help`、`/quit`
9. `/sessions list`

普通文本行视为任务输入。

## 6. 运行态设计

### 6.1 Runtime 组成

`ClientRuntime` 统一封装：

1. `agent`：由 `DareAgentBuilder` 构建。
2. `channel`：`AgentChannel.build(DirectClientChannel)`。
3. `client_channel`：对外 action/control 请求与事件轮询通道。
4. `config_provider`、`config`：最终生效配置与来源。
5. `model`、`options`：模型适配器实例与 CLI 运行参数。

### 6.2 执行模式

1. **execute 模式**：任务直接进入 `agent(Message(...), transport=channel)`。
2. **plan 模式**：
   - 先调用 `DefaultPlanner.plan(ctx)` 预览。
   - 用户 `/approve` 后再执行任务。

### 6.3 后台执行与并发

交互模式下任务执行可后台运行（`asyncio.create_task`），允许同时执行：

1. `/status` 查询
2. `/approvals poll|grant|deny|revoke`
3. `/interrupt`

### 6.4 Session Snapshot And Resume

`client/` 需要把“单进程内 STM 连续性”提升为“跨进程可恢复”的 CLI contract。

第一版设计：

1. session snapshot 固定写到 `<workspace_dir>/.dare/sessions/<session-id>.json`
2. snapshot 至少包含：
   - `schema_version`
   - `session_id`
   - `mode`
   - `created_at`
   - `updated_at`
   - `workspace_dir`
   - `messages`
3. `chat/run/script` 都支持 `--resume [session-id|latest]`
4. `chat/run/script` 同时支持 `--session-id <session-id>` 兼容入口，等价于 `--resume <session-id>`
5. `--resume` 不带值时默认解析为 `latest`
6. `--resume` 与 `--session-id` 目标冲突时返回参数错误

恢复边界：

1. 会恢复：STM/history、`session_id`、`mode`
2. 不恢复：`pending_plan`、`pending_task_description`、`pending_runtime_approvals`、后台 task
3. 恢复后 `CLISessionState.status` 统一回到 `idle`

这样可以对齐 Claude/Codex CLI 的基础“继续上一次对话”体验，同时避免把 runtime checkpoint 语义混进 CLI session restore。

## 7. 配置模型与优先级

### 7.1 来源

1. CLI flags（最高）
2. workspace `.dare/config.json`（覆盖 user）
3. user `.dare/config.json`
4. 代码默认值（最低）

### 7.2 关键字段

1. `workspace_dir`、`user_dir`
2. `llm.adapter/model/api_key/endpoint/proxy`
3. `cli.log_path`
4. `mcp_paths`、`allow_mcps`
5. `default_prompt_id`
6. `system_prompt.mode/content/path`（支持 `replace|append`；可由 CLI flags 临时覆盖）

### 7.3 一致性原则

CLI 层不自行定义“平行配置模型”，只对 `Config` 做覆盖合并，最终统一传入 builder。

## 8. 输出与退出码

### 8.1 输出模式

1. `--output human`（默认）：终端仅保留交互内容；日志统一落盘到 `cli.log_path`（默认 `./dare.log`）。
   - `chat` 模式下执行期间默认不重复显示 prompt；仅在任务完成后重新给出 `dare>` 输入提示。
   - 若执行中触发工具审批，CLI 直接以内联 `approve>` 提示收集 `y/n` 决策，再通过 `approvals:*` action 提交到底层审批管理器。
2. `--output json`：结构化 JSON，便于自动化集成。

### 8.2 标准退出码

1. `0`：成功
2. `1`：业务执行失败（任务失败、审批超时/拒绝、运行时 action 错误）
3. `2`：参数或输入错误（argparse 参数错误、路径/脚本读取错误）
4. `3`：`doctor` 检查失败（环境或配置探测失败）
5. `130`：用户中断（Ctrl+C）

resume 相关错误保持落在退出码 `2`：

1. `--resume latest` 但没有任何 snapshot
2. `--resume <session-id>` 找不到目标文件
3. snapshot JSON 损坏或 `schema_version` 不兼容

### 8.3 宿主编排协议基线（planned）

> 本节记录 Issue #135 宿主编排协议的当前设计基线。  
> 其中 `8.3.3` 已在 Slice B 落地，`8.3.4`/`8.3.5` 的最小 control baseline 已在 Slice C 落地；capability discovery 仍保留给后续 Slice D。

#### 8.3.1 模式分层

| 模式 | 状态 | 入口 | 主要语义 |
|---|---|---|---|
| interactive | landed | `dare chat` | 允许 `dare>` prompt、内联审批提示、人类可读输出。 |
| automation-json | landed / legacy | `run/script --output json` | 允许脚本消费 `log/event/result` 行输出，但不承诺宿主级稳定 envelope。 |
| headless | landed | `run/script --headless` | 禁止 prompt、禁止内联审批提示，输出 versioned event envelope，并可选开启 `--control-stdin` 宿主控制面。 |

#### 8.3.2 核心流程

```text
Host Process
   |
   | start CLI in headless mode
   v
DARE client
   |
   | emits versioned event envelope
   v
Host Event Parser
   |
   | sends structured command frames via control-stdin
   v
DARE control handler
   |
   | returns structured result/error frame
   v
Host Orchestrator
```

headless 目标流程要求：

1. 启动后先输出 `session.started` 或等价握手事件。
2. 执行期间所有可观察状态都走结构化事件帧，而不是 `[INFO]` / prompt 文案。
3. 审批、MCP、skills、能力发现等控制请求通过独立 control plane 完成，而不是依赖交互文本命令。

#### 8.3.3 事件 envelope v1（Slice B landed baseline）

当前已落地的宿主事件帧顶层字段：

1. `schema_version`
2. `ts`
3. `session_id`
4. `run_id`
5. `seq`
6. `event`
7. `data`

当前已落地的事件类别基线：

1. lifecycle：`session.started`、`task.started`、`task.completed`、`task.failed`
2. tool/model：`model.response`、`tool.invoke`、`tool.result`、`tool.error`
3. approvals：`approval.pending`、`approval.resolved`
4. diagnostic / fallback：`log.*`、`transport.raw`

兼容原则：

1. 当前 `--output json` 行结构视为 legacy automation schema。
2. headless envelope 使用独立 schema version，不直接复用现有 `type=log|event|result` 结构。
3. 当前 landed 行为覆盖结构化事件流、`control-stdin` 最小控制面，以及显式 `actions:list` capability discovery；只有 startup handshake 与动态 MCP 事件仍属于后续 Slice。

#### 8.3.4 control-stdin v1（Slice C landed baseline）

v1 设计选择：优先支持 `--control-stdin`，即 stdin 一行一个 JSON 命令帧。

命令 envelope 最小字段：

1. `schema_version`
2. `id`
3. `action`
4. `params`

结果 envelope 最小字段：

1. `schema_version`
2. `id`
3. `ok`
4. `result`
5. `error`

协议约束：

1. `schema_version` 固定为 `client-control-stdin.v1`
2. control result/error 与 headless event 一样走 `stdout` 多路复用，由 `schema_version` 区分
3. `status:get` 的最小返回字段包含 `mode`、`status`、`running`、`active_task`、`pending_approvals`
4. `session:resume` 的成功返回至少包含 `requested`、`session_id`、`mode`、`restored_messages`、`previous_session_id`

当前 landed action 基线：

1. `actions:list`
2. `status:get`
3. `session:resume`（仅 idle 状态可用）
4. `approvals:list/poll/grant/deny/revoke`
5. `mcp:list/reload/show-tool`
6. `skills:list`

当前 capability discovery 基线：

1. v1 capability discovery 优先走显式 `actions:list`，继续复用 `client-control-stdin.v1`
2. landed `actions:list` 返回当前 CLI host protocol surface 的 canonical action ids，不要求首版附带额外元数据矩阵
3. unsolicited startup handshake 不纳入当前宿主协议基线，避免在 stdout 多路复用流上引入额外隐式帧

#### 8.3.5 错误处理与安全边界（Slice C landed baseline）

1. `run/script --headless` 已禁止回落到 `input("dare> ")` 或内联 `approve>` 提示；审批等待超时会返回结构化 `task.failed` 事件。
2. control plane 的失败必须返回结构化错误对象，而不是只写 stdout 文案。
3. 宿主协议层不得绕过已有 `approvals:*` / `mcp:*` / `skills:*` action 语义，只能在 CLI 外层做协议桥接。
4. 若未来补 `--control-port`，必须额外定义 loopback 约束、调用方身份与审计关联；该能力不属于当前 Slice A 的设计承诺。

## 9. 安全与边界

1. 审批规则存储继续复用：
   - workspace: `<workspace_dir>/.dare/approvals.json`
   - user: `<user_dir>/.dare/approvals.json`
2. 所有审批操作走 `approvals:*` action，不直接篡改存储文件。
3. MCP 动态重载使用 `agent.reload_mcp(...)`，不在 CLI 层自行管理 provider 生命周期。
4. 任务执行默认保留工具安全策略，不新增隐式“跳过审批”逻辑。

## 10. 测试策略

### 10.1 单元测试（`tests/unit/test_client_*.py`）

1. 命令解析（含 `key=value`、引号参数）。
2. 配置覆盖优先级。
3. action/control 响应解析。
4. session 状态机（plan/approve/reject/background）。
5. session snapshot / `--resume` 选择与错误语义。
6. 输出渲染（human/json）。

### 10.2 集成测试

1. `run` 一次性任务路径（mock model）。
2. `chat` + 后台执行 + approvals 命令并发。
3. `mcp reload/unload` 行为（mock MCP manager 或本地 fake server）。
4. `script` 模式（注释/空行/失败中断）。
5. headless 协议稳定性（事件 envelope、schema version、error path）。
6. `control-stdin` 往返控制（session resume / approvals / MCP / skills / status）。
7. capability discovery（显式 `actions:list`）与宿主降级策略。

## 11. 分阶段落地计划

### Phase 1（MVP，可用）

1. `chat/run/script`
2. `/mode plan|execute`、`/approve`、`/reject`、`/status`
3. `approvals` 全命令
4. `mcp list/inspect/reload/unload`
5. `tools list`、`config show`、`model show`

### Phase 2（增强）

1. `skills list`、`control` 命令
2. `--output json` 全面覆盖
3. `doctor` 环境诊断（依赖/API key/配置有效性）

### Phase 3（发布化）

1. 打包入口（console script）
2. 完整命令文档与示例脚本
3. 回归测试矩阵接入 CI

### Phase 4（宿主编排协议，planned）

1. `--headless` 明确模式边界
2. versioned event envelope v1
3. `--control-stdin` 最小外部控制面
4. 显式 capability discovery（`actions:list`）
5. 启动握手若要引入，需作为后续独立 slice 明确多路复用与兼容策略

## 12. 风险与缓解

1. **风险：示例 CLI 逻辑重复迁移导致回归**
   - 缓解：先抽象公共模块，再适配命令；用回归测试覆盖现有关键行为。
2. **风险：transport action 响应格式理解偏差**
   - 缓解：统一在 `action_client.py` 做解析与 schema 归一化。
3. **风险：模型依赖差异（openrouter/openai）导致启动失败**
   - 缓解：`doctor` 与启动前检查给出明确错误与修复建议。

## 13. 里程碑验收标准

满足以下条件即认为 `client` CLI 一期完成：

1. 能在空白工作区启动 `chat` 并执行任务。
2. 能在执行中完成审批 `poll -> grant/deny` 闭环。
3. 能动态 `mcp reload` 并查询到新工具。
4. 脚本模式可稳定复现演示流程。
5. 关键命令均有单元测试与至少一条集成测试。
