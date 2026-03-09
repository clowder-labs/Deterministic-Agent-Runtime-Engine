# 07-tool-approval-memory

演示工具授权记忆（approval memory）的完整链路：

1. 首次 `requires_approval=true` 的工具调用进入 pending。
2. 通过 action `approvals:grant` 授权并写入规则。
3. 后续命中规则的调用自动放行（不再重复审批）。
4. 通过 `approvals:revoke` 撤销后，调用再次回到 pending。

这个示例是**确定性脚本模型**，不依赖外部 LLM API，直接可跑。

## 运行

```bash
cd examples/07-tool-approval-memory
python main.py
```

## 你会看到什么

- 第一次 run：先收到 `select(kind=ask, domain=approval)` 通知并打印 `pending request: ...`，随后调用 `approvals:grant`。
- 第一次 run 同时演示 `approvals:poll`（控制面阻塞拉取待审批请求）。
- 第二次 run：`pending_count=0`（自动放行）。
- 撤销规则后第三次 run：再次出现 `pending request after revoke: ...`。
- 末尾打印当前 `pending/rules` 状态和规则文件路径。

## 关键代码要点

- Agent 侧：`DareAgentBuilder(...).with_config(...).add_tools(RunCommandTool())`
- 通道侧：`DirectClientChannel + AgentChannel`
- 审批 action：
  - `approvals:list`
  - `approvals:poll`（可选 `session_id` 过滤）
  - `approvals:grant`
  - `approvals:revoke`
- 规则持久化路径：
  - `workspace/.dare/approvals.json`
  - `workspace/demo-user-home/.dare/approvals.json`

## 文件结构

```text
07-tool-approval-memory/
├── main.py
└── README.md
```

运行时会自动创建 `workspace/` 用于演示审批规则持久化文件。
