# Example 09: Plan Agent + 两类 sub-agent

Skill 源使用 **config.skill_paths**（本示例为 `D:\Agent\skills\skills`），不手写 skill。

- **Plan Agent**：仅 plan tools（无 search_skill、MCP、native tools）。
- **sub_agent_general**（通用）：native + MCP + auto skill，可 `search_skill` 到该路径下**每一种** skill。
- **sub_agent_special_{id}**（专用）：为 `skill_paths` 下的**每一种** skill 各创建一个 sub-agent，该 skill 常驻其 system prompt；native + MCP。

## 配置

- `.dare/config.json`：`mcp_paths`（含 local_math）、`skill_paths`
- `.dare/mcp/local_math.json`：本地数学 MCP（http://127.0.0.1:8765/）
- `local_mcp_server.py`：与 05 一致，需在**另一终端**先启动

## 运行

```bash
# 终端 1：先启动 MCP 服务
cd examples/09-plan-agent-with-subagents
python local_mcp_server.py

# 终端 2：再运行 main
cd examples/09-plan-agent-with-subagents
python main.py
```

默认任务对 **agentscope/examples/agent/a2a_agent** 做代码侦察，产出 workspace/a2a_agent_recon.md。自定义：`python main.py "任务描述"`。
