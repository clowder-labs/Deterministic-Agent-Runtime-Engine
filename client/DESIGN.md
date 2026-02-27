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

## 3. 总体方案

### 3.1 关键决策

1. **CLI 解析库使用 `argparse`**：保持零新增核心依赖，与现有示例一致。
2. **执行与控制解耦**：
   - 任务执行使用 `agent(Task(...), transport=channel)`，保留 `Task.metadata`（如 `conversation_id`）。
   - 查询/控制统一走 transport action/control（`approvals:*`、`mcp:*`、`config:get` 等）。
3. **单进程内 transport 适配**：
   - 使用 `DirectClientChannel + AgentChannel.build(...)`，确保 action/control 协议一致。
4. **默认安全策略**：
   - 高风险工具审批默认开启（复用 `ToolApprovalManager` 默认行为）。
   - 不提供默认绕过审批的开关。

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
dare chat [options]
dare run --task "..."
dare script --file demo.txt

dare approvals list
dare approvals poll [--timeout-ms 30000]
dare approvals grant <request_id> [--scope workspace] [--matcher exact_params] [--matcher-value ...]
dare approvals deny  <request_id> [--scope once]      [--matcher exact_params] [--matcher-value ...]
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

1. **execute 模式**：任务直接进入 `agent(Task(...), transport=channel)`。
2. **plan 模式**：
   - 先调用 `DefaultPlanner.plan(ctx)` 预览。
   - 用户 `/approve` 后再执行任务。

### 6.3 后台执行与并发

交互模式下任务执行可后台运行（`asyncio.create_task`），允许同时执行：

1. `/status` 查询
2. `/approvals poll|grant|deny|revoke`
3. `/interrupt`

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
5. 输出渲染（human/json）。

### 10.2 集成测试

1. `run` 一次性任务路径（mock model）。
2. `chat` + 后台执行 + approvals 命令并发。
3. `mcp reload/unload` 行为（mock MCP manager 或本地 fake server）。
4. `script` 模式（注释/空行/失败中断）。

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
