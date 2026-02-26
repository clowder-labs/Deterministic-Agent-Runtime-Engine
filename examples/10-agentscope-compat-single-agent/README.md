# Example 10: AgentScope → DARE 迁移验证

验证在 `dare_framework` 中替换 AgentScope 单 agent 场景的可行性，逐能力分析差距。

## 覆盖的 12 项 AgentScope 能力

| # | AgentScope 能力 | DARE 实现 | 评级 | 关键 Gap |
|---|----------------|-----------|------|---------|
| 1 | `ReActAgent` | `ReactAgent` | E0 | Gap-R1(并行tool), Gap-R5(自动压缩) |
| 2 | `Msg` | `CompatMsg` 桥接 | E1 | **Gap-M1**(tag), Gap-M3(id) |
| 3 | `TextBlock` | `TextBlock` TypedDict | E1 | 依赖 Gap-M2 |
| 4 | `Tool/Toolkit` | `ITool + ToolGateway` | E0 | Gap-T1(流式) |
| 5 | `InMemoryMemory` | `CompatMemoryWrapper` | E1 | **Gap-Mem1**(mark), **Gap-Mem5**(tool pair) |
| 6 | `ChatModelBase` | `CompatFormattedModelAdapter` | E0/E2 | **Gap-LM1(P0)**(thinking), Gap-LM2(stream) |
| 7 | `PlanNoteBook` | `CompatPlanNotebook` + 6 tools | E1 | Gap-P1(status), Gap-P5(序列化) |
| 8 | `SubTask` | `CompatSubTask` | E1 | 合并于 Gap-P1 |
| 9 | `TruncatedFormatterBase` | `CompatTruncatedFormatter` | E1 | **Gap-F1**(tool pair safe), Gap-F2(token) |
| 10 | `Knowledge` | `create_knowledge(rawdata)` | E0 | Gap-K1(embedding adapter) |
| 11 | `HttpStatefulClient` | `HttpStatefulClientShim` | E1 | Gap-H3(缓存) |
| 12 | `Session` | `JsonSessionBridge` | E2 | **Gap-S1**(StateModule), **Gap-S2**(ISessionStore) |

**详细分析**：[`DESIGN.md`](./DESIGN.md) | **框架 Gap 分析**：[`docs/design/archive/agentscope-migration-framework-gaps.md`](../../docs/design/archive/agentscope-migration-framework-gaps.md)

## 文件结构

```
compat_agent.py   — 兼容层核心（12 项能力映射 + Gap stub 声明）
simple_loop.py    — 最简 ReAct 循环（non-transport）
cli.py            — Transport CLI（save/load/status/help）
main.py           — 入口（委托 simple_loop）
DESIGN.md         — 设计文档（逐能力差异矩阵）
demo_script.txt   — 脚本模式示例
```

## 运行

### 1) 最简循环

```bash
cd examples/10-agentscope-compat-single-agent
export OPENROUTER_API_KEY="your-api-key"
python main.py
```

### 2) Transport CLI

```bash
python cli.py                                    # 交互模式
python cli.py --task "验证单 agent 能力"           # 单条任务
python cli.py --script demo_script.txt            # 脚本模式
```

CLI 命令：`/help` `/status` `/save [id]` `/load [id]` `/quit`

## 测试

```bash
.venv/bin/pytest -q tests/unit/test_example_10_agentscope_compat.py
```

8 项测试覆盖：消息 roundtrip、截断 tool pair 安全、Session save/load、HTTP shim、
简单循环、完整 demo 流程、transport 循环、CLI 脚本模式。
