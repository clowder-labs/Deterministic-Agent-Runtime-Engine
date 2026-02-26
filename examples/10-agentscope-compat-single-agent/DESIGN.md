# Example 10 Design: AgentScope → DARE 兼容性验证

## 1. 目标

基于 `dare_framework` 构建一个可运行单 Agent，**逐能力验证** AgentScope 12 项核心能力的可替换性，明确标注每项能力的差距和补齐状态。

目标能力集合：
`ReActAgent / Msg / TextBlock / Tool / InMemoryMemory / ChatModelBase /
PlanNoteBook / SubTask / TruncatedFormatterBase / Knowledge / HttpStatefulClient / Session`

## 2. 验收标准

### 评级体系

| 级别 | 含义 | 行动 |
|------|------|------|
| **E0** | 原生等价 | 直接使用 DARE 原生能力 |
| **E1** | 语义等价（需适配层） | Example 内兼容层实现 |
| **E2** | 不等价（需框架增强） | Example 提供 stub/workaround，框架层需补齐 |

### 通过标准

1. 单 agent 完成 ReAct 循环（reason → tool call → observe → final）
2. 12 项能力全部有：差距说明、当前状态、补齐方案
3. 两种运行形态均可工作：non-transport 循环 + transport CLI
4. 所有已知 Gap 有对应 Gap ID 和优先级

## 3. 证据基线

**AgentScope**（固定 commit `f6db16547215ea580e85e362126a5ea20fd54cd4`）：
- [ReActAgent](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/agent/_react_agent.py)
- [Msg/TextBlock](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/message/_message_base.py)
- [Tool/Toolkit](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/tool/_toolkit.py)
- [InMemoryMemory](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/memory/_working_memory/_in_memory_memory.py)
- [ChatModelBase](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/model/_model_base.py)
- [PlanNoteBook](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/plan/_plan_notebook.py)
- [SubTask](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/plan/_plan_model.py)
- [TruncatedFormatterBase](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/formatter/_truncated_formatter_base.py)
- [Knowledge](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/rag/_knowledge_base.py)
- [HttpStatefulClient](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/mcp/_http_stateful_client.py)
- [Session](https://github.com/agentscope-ai/agentscope/blob/f6db16547215ea580e85e362126a5ea20fd54cd4/src/agentscope/session/_session_base.py)

**DARE framework** 本地证据（关键文件）：
- Agent: `dare_framework/agent/react_agent.py`, `dare_framework/agent/builder.py`
- Message/Context: `dare_framework/context/types.py`
- Model: `dare_framework/model/types.py`, `dare_framework/model/adapters/openrouter_adapter.py`
- Tool: `dare_framework/tool/kernel.py`, `dare_framework/tool/tool_gateway.py`
- Memory: `dare_framework/memory/in_memory_stm.py`
- Knowledge: `dare_framework/knowledge/kernel.py`
- Plan: `dare_framework/plan_v2/types.py`, `dare_framework/plan_v2/tools.py`
- Compression: `dare_framework/compression/core.py`
- MCP: `dare_framework/mcp/client.py`, `dare_framework/mcp/transports/http.py`

## 4. 能力差异矩阵（详细版）

### 4.1 ReActAgent [E0 — 原生等价]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 循环结构 | `_reasoning() → _acting() → repeat` | `assemble() → generate() → tool calls → repeat` | 等价 |
| 最大迭代 | `max_iterations=20` | `max_tool_rounds=10` | 等价（值不同） |
| 并行 tool 执行 | `parallel_tool_calls=True` → `asyncio.gather` | 仅串行 | **Gap-R1** |
| 自动内存压缩 | `_compress_memory_if_needed()` 每轮触发 | 无自动压缩 | **Gap-R5** |
| 超时 fallback | 超 max_iterations 做 summarization | 返回"未收敛"文本 | Gap-R2 |
| Plan 注入 | `plan_to_hint()` 生成 `<system-hint>` | `critical_block` 注入 | 接近等价 |
| Hook 粒度 | pre/post_reasoning, pre/post_acting | session/milestone/plan/tool 级 | Gap-R4 |
| Loop guard | 无 | 检测连续 3 次完全相同 tool call | DARE 更好 |

**Example 实现**：直接用 `BaseAgent.react_agent_builder("example-10-agent")`

---

### 4.2 Msg [E1 — 需适配层]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 字段 | `id, name, role, content, metadata, timestamp, invocation_id` | `role, content, name, metadata` | **Gap-M3**(id), Gap-M4(timestamp) |
| content 类型 | `str \| list[ContentBlock]` | `str` only | **Gap-M2** |
| 消息标签 | 通过 Memory mark 系统 | 无 | **Gap-M1** |
| 序列化 | `to_dict() / from_dict()` | 无标准方法 | **Gap-M5** |

**Example 实现**：`CompatMsg` 双向桥接，`_compat_id`/`_compat_tag` 通过 metadata 模拟

---

### 4.3 TextBlock [E1 — 需适配层]

与 Gap-M2 关联。Example 定义 `TextBlock = TypedDict` + `ThinkingBlock` stub。

---

### 4.4 Tool/Toolkit [E0 — 原生等价]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 注册方式 | `Toolkit.register_tool_function()` | `ITool` 类 + `add_tools()` | 风格不同，等价 |
| Schema 推断 | 从 docstring | 从类型注解 | DARE 更严格 |
| 流式结果 | `ToolResponse(stream=True)` | `ToolResult`（单值） | **Gap-T1** |
| 中间件 | onion-style middleware | 无 | Gap-T2 |
| 预设参数 | `preset_kwargs` | 无 | Gap-T3 |
| 分组管理 | `ToolGroup` 启用/禁用 | `change_capability_status()` | 等价 |

**Example 实现**：`CreatePlanNotebookTool`, `FinishPlanTool`, `RevisePlanTool`, `EchoTool` 等

---

### 4.5 InMemoryMemory [E1 — 需适配层]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 存储 | `list[(Msg, marks)]` | `list[Message]` | **Gap-Mem1** |
| Mark 系统 | `update_messages_mark()` 按 ID 打标 | 无 | **Gap-Mem1** |
| 过滤检索 | `get_memory(mark=, exclude_mark=)` | `get(query)` 无过滤 | **Gap-Mem1** |
| 压缩摘要 | `_compressed_summary` + `prepend_summary` | 无 | **Gap-Mem2** |
| 序列化 | `state_dict() / load_state_dict()` | 无 | **Gap-Mem3** |
| 按 ID 操作 | `delete(ids)`, `delete_by_mark()` | 仅 `clear()` | **Gap-Mem4** |
| 压缩安全 | 压缩时保护 tool pair | 无保护 | **Gap-Mem5** |

**Example 实现**：`CompatMemoryWrapper` 在 Context/STM 之上模拟 mark 和 summary

---

### 4.6 ChatModelBase [E0 — 原生等价 (核心), E2 — thinking/stream]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 基础调用 | `__call__() → ChatResponse` | `generate() → ModelResponse` | 等价 |
| 流式输出 | `__call__(stream=True) → AsyncGenerator` | 无 | **Gap-LM2** |
| Thinking 提取 | `ChatResponse` 含 `ThinkingBlock` | `ModelResponse` 无 `thinking_content` | **Gap-LM1 (P0)** |
| Adapter 种类 | 6 种（OpenAI/Anthropic/Gemini/DashScope/Ollama/Trinity） | 2 种（OpenAI-LangChain/OpenRouter） | Gap-LM3 |
| Reasoning tokens | 规范化到 usage | 未提取 | **Gap-LM4** |

**Example 实现**：`CompatFormattedModelAdapter` 包装，`generate_stream()` stub

---

### 4.7 PlanNoteBook [E1 — 需适配层]

| 维度 | AgentScope | DARE plan_v2 | 差距 |
|------|-----------|-------------|------|
| 工具数量 | 8 个 | 6 个 | **Gap-P2**(finish_plan), **Gap-P3**(revise) |
| Step 状态 | `SubTask.state: todo/in_progress/done/abandoned` | `Step`: 无状态字段 | **Gap-P1** |
| 计划状态 | `Plan.state: todo/in_progress/done/abandoned` | 无计划级状态 | **Gap-P2** |
| 历史管理 | `view_historical_plans / recover_historical_plan` | 无 | Gap-P4 |
| 序列化 | `state_dict()` 继承 StateModule | 无 | **Gap-P5** |
| Change hooks | `plan_change_hooks` | 无 | Gap-P6 |
| Hint 注入 | `DefaultPlanToHint → <system-hint>` | `critical_block` 注入 | Gap-P7 |
| 修改计划 | `revise_current_plan(add/revise/delete)` | `CreatePlanTool` 拒绝覆盖 | **Gap-P3** |

**Example 实现**：`CompatPlanNotebook` + `CompatSubTask` + 完整 tool provider (6 个工具)

---

### 4.8 SubTask [E1 — 需适配层]

与 Gap-P1 合并。`CompatSubTask` 实现完整生命周期。

---

### 4.9 TruncatedFormatterBase [E1 — 需适配层]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 截断单位 | Token 数 | 消息条数 | **Gap-F2** |
| Tool pair 安全 | 成对删除 | 无保护 | **Gap-F1** |
| 自动触发 | 每次 `_reasoning()` 前 | 手动调用 | **Gap-F4** |
| Provider 格式化 | OpenAI/Anthropic/Gemini/... formatter 子类 | 无 | Gap-F3 |
| 标签感知 | 跳过 important 消息 | 无标签概念 | 依赖 Gap-M1 |

**Example 实现**：`CompatTruncatedFormatter`（字符级 + tool pair 安全）

---

### 4.10 Knowledge [E0 — 原生等价 (rawdata), E2 — vector]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 向量检索 | `SimpleKnowledge.retrieve()` | `VectorKnowledge.get()` | 功能等价 |
| Embedding adapter | 多种 model | 仅 `OpenAIEmbeddingAdapter` (LangChain) | **Gap-K1** |
| 同步/异步 | `async retrieve()` | `get()` 同步 | **Gap-K2** |
| 文档加载器 | 有 reader/scraper | 无 | Gap-K3 |
| Score 阈值 | `score_threshold` 参数 | 无 | Gap-K4 |

**Example 实现**：直接用 `create_knowledge({"type": "rawdata"})` — rawdata 模式

---

### 4.11 HttpStatefulClient [E1 — 需适配层]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| Facade API | `connect/close/list_tools/get_callable_function` | `MCPClient + HTTPTransport` | Gap-H1 |
| 工具缓存 | `_cached_tools` | 每次请求 | Gap-H3 |
| 自动重连 | 无 | 无 | Gap-H2 |

**Example 实现**：`HttpStatefulClientShim`（含工具缓存）

---

### 4.12 Session [E2 — 需框架增强]

| 维度 | AgentScope | DARE | 差距 |
|------|-----------|------|------|
| 协议 | `StateModule(state_dict/load_state_dict)` | 无 | **Gap-S1** |
| 存储接口 | `SessionBase.save/load(**state_modules)` | 无 | **Gap-S2** |
| 后端 | JsonSession + RedisSession | 无（仅 CheckpointStore） | Gap-S3 |
| 自动收集 | `AgentBase._AgentMeta` 自动发现 StateModule | 无 | 设计差异 |

**Example 实现**：`JsonSessionBridge`（手动序列化 STM + notebook）

## 5. 框架层 Gap 汇总（共 40+ 个）

完整分析见：[`docs/design/archive/agentscope-migration-framework-gaps.md`](../../docs/design/archive/agentscope-migration-framework-gaps.md)

### P0（阻断性）
- **Gap-LM1**: `ModelResponse` 无 `thinking_content`

### P1（高优先）
- **Gap-M1**: Message 无 tag/mark
- **Gap-Mem1/2/5**: InMemorySTM 无 mark/summary/tool-pair-safe compress
- **Gap-F1/F4**: compress_context 无 tool pair 安全/无自动触发
- **Gap-R5**: ReactAgent 无自动内存压缩
- **Gap-LM4**: Usage 不规范化 reasoning_tokens
- **Gap-S1/S2**: 无 StateModule/ISessionStore

### P2（中优先）
- **Gap-M3/M5**: Message 无 id/无序列化
- **Gap-Mem3/4**: STM 无 state_dict/无按 ID 操作
- **Gap-LM2**: 无 generate_stream
- **Gap-P1/2/3/5**: Step 无 status / 缺工具 / 无序列化
- **Gap-F2**: 无 token 级截断
- **Gap-K2**: Knowledge get() 同步/异步阻抗

## 6. 运行架构

### 6.1 基础循环（non-transport）

```
用户输入 → STM.add(user msg)
→ ReactAgent.execute():
    → Context.assemble() → model.generate()
    → if tool_calls → ToolGateway.invoke() → STM.add(tool result) → repeat
    → if no tool_calls → return RunResult
→ 输出最终答复
```

实现：`simple_loop.py` / `main.py`

### 6.2 Transport CLI

```
用户输入 → parse_command()
→ if /command → 本地处理（help/status/save/load/quit）
→ else → DirectClientChannel.ask(envelope) → AgentChannel → agent.execute()
→ parse_response() → 输出
```

实现：`cli.py`

## 7. 验证清单

| 验证项 | 状态 | 测试 |
|--------|------|------|
| Msg/TextBlock roundtrip | PASS | `test_compat_msg_roundtrip` |
| TruncatedFormatter tool pair 安全 | PASS | `test_truncated_formatter_truncates_and_preserves_tool_pairs` |
| PlanNotebook/SubTask 生命周期 | PASS | `test_single_agent_demo_flow_runs_with_equivalent_capabilities` |
| Session save/load roundtrip | PASS | `test_json_session_bridge_roundtrip` |
| HttpStatefulClient shim 构造 | PASS | `test_http_stateful_client_shim_metadata` |
| Basic ReAct loop | PASS | `test_simple_loop_builder_runs_one_react_cycle` |
| Transport message loop | PASS | `test_single_agent_demo_transport_message_loop` |
| CLI script mode | PASS | `test_example_10_cli_script_mode_uses_transport` |
