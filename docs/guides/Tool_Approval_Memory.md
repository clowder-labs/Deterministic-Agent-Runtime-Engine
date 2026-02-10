# Tool Approval Memory 开发者指南

## 1. 能力目标

`Tool Approval Memory` 解决的是高风险工具（`requires_approval=true`）的重复审批问题：

- 首次调用进入 pending，等待外部客户端决策。
- 决策可沉淀为规则（session/workspace/user），后续命中自动放行或自动拒绝。
- 规则可撤销，撤销后立即恢复人工审批。

这套机制是按成熟 coding agent 的控制面方式设计：**模型不直接决定是否跳过审批**，审批状态由运行时控制面管理。

## 2. 默认接线（开箱即用）

当我们使用任意 Agent Builder 并提供 `Config` 时，Builder 会自动创建 `ToolApprovalManager`：

- 代码入口：`dare_framework/agent/builder.py`
- 创建逻辑：`ToolApprovalManager.from_paths(workspace_dir=config.workspace_dir, user_dir=config.user_dir)`
- action 暴露：
  - `approvals:list`
  - `approvals:grant`
  - `approvals:deny`
  - `approvals:revoke`

其中真正执行审批门控的是 `DareAgent` 的 Tool Loop（`dare_framework/agent/dare_agent.py`），会在工具调用前检查 `requires_approval` 元数据。

## 3. 规则作用域与匹配策略

### 3.1 Scope

- `once`：仅当前 pending request，**不落盘**。
- `session`：当前 run/session 生命周期内有效，内存态。
- `workspace`：落盘到 `<workspace_dir>/.dare/approvals.json`。
- `user`：落盘到 `<user_dir>/.dare/approvals.json`。

### 3.2 Matcher

- `capability`：按能力 ID（例如 `run_command`）匹配。
- `exact_params`：按参数 canonical JSON 哈希匹配。
- `command_prefix`：按 `params.command` 前缀匹配（适合命令族放行）。

### 3.3 匹配顺序与冲突处理

- 作用域扫描顺序：`once -> session -> workspace -> user`
- 冲突优先级：同一调用如果同时命中 allow 和 deny，**deny 优先**。

## 4. Action API（给控制面/客户端）

### 4.1 `approvals:list`

输入：无

输出：

```json
{
  "pending": [
    {
      "request_id": "...",
      "capability_id": "run_command",
      "params": {"command": "echo hi"},
      "params_hash": "...",
      "command": "echo hi",
      "session_id": "...",
      "reason": "Tool run_command requires approval",
      "created_at": 1730000000.0
    }
  ],
  "rules": [
    {
      "rule_id": "...",
      "capability_id": "run_command",
      "decision": "allow",
      "scope": "workspace",
      "matcher": "command_prefix",
      "matcher_value": "echo",
      "created_at": 1730000001.0,
      "session_id": null
    }
  ]
}
```

### 4.2 `approvals:grant`

必填参数：`request_id`

可选参数（含默认值）：

- `scope`：默认 `workspace`
- `matcher`：默认 `exact_params`
- `matcher_value`：仅 `command_prefix` 等策略需要显式传入

### 4.3 `approvals:deny`

必填参数：`request_id`

可选参数（含默认值）：

- `scope`：默认 `once`
- `matcher`：默认 `exact_params`
- `matcher_value`：同上

### 4.4 `approvals:revoke`

必填参数：`rule_id`

输出：`{"rule_id": "...", "removed": true|false}`

## 5. 接入示例（推荐）

完整可运行示例见：`examples/07-tool-approval-memory/main.py`

这个示例展示了完整闭环：

1. 发起一次 `run_command`，产生 pending。
2. 通过 `approvals:grant(scope=workspace, matcher=command_prefix)` 放行并落盘。
3. 二次调用自动放行（无 pending）。
4. `approvals:revoke` 后再次进入 pending。

## 5.1 CLI 快速操作（05/06 示例）

`examples/05-dare-coding-agent-enhanced/cli.py` 与 `examples/06-dare-coding-agent-mcp/cli.py` 都支持：

- `/approvals list`
- `/approvals grant <request_id> [scope=workspace] [matcher=exact_params] [matcher_value=...]`
- `/approvals deny <request_id> [scope=once] [matcher=exact_params] [matcher_value=...]`
- `/approvals revoke <rule_id>`

推荐交互流程：

1. 在 `dare>` 输入任务，让 Agent 进入执行。
2. 若任务命中审批门控，执行 `/approvals list` 找到 `request_id`。
3. 根据策略执行 `grant/deny`。
4. 用 `/status` + `/approvals list` 验证任务与规则状态。

注意：在交互模式中，任务执行默认后台运行，因此我们可以在执行过程中继续输入审批命令。

## 6. 代码中显式注入 Approval Manager（可选）

如果我们要自定义存储路径或测试桩，可以显式注入：

```python
from dare_framework.agent import DareAgentBuilder
from dare_framework.tool._internal.control.approval_manager import ToolApprovalManager

approval_manager = ToolApprovalManager.from_paths(
    workspace_dir="/path/to/workspace",
    user_dir="/path/to/user-home",
)

agent = (
    DareAgentBuilder("my-agent")
    .with_model(model)
    .with_config(config)
    .with_approval_manager(approval_manager)
    .add_tools(...)
    .build()
)
```

## 7. 生产建议

- 优先使用 `exact_params`，最小权限原则最稳妥。
- 仅在确有必要时使用 `command_prefix` 和 `capability`。
- 对破坏性操作建议配 deny 规则，并通过 `approvals:list` 做可观测。
- CI/自动化场景里，建议将 workspace/user 目录显式隔离，避免跨任务污染审批记忆。

## 8. 常见问题

- `approvals list` 一直是空：
  - 先确认当前任务是否真的调用了 `requires_approval=true` 的能力。
- `grant/deny` 提示 `Unknown approval request`：
  - 该请求可能已被处理或超出当前会话上下文；先重新 `approvals list`。
- 规则不生效：
  - 检查 matcher 是否与调用形态一致（尤其 `command_prefix`）。
- 重启后规则丢失：
  - `once/session` 本来就是内存态；需要持久化请使用 `workspace` 或 `user` scope。
