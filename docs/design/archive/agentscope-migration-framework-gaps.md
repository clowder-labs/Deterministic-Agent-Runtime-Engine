# AgentScope → DARE 框架迁移：完整差距分析与补齐路线

> 文档状态：v2 — 深度分析完成，待逐项实施
> 关联 Example：`examples/10-agentscope-compat-single-agent/`
> AgentScope 参考 commit：`f6db16547215ea580e85e362126a5ea20fd54cd4`
> AgentScope 仓库：https://github.com/agentscope-ai/agentscope

---

## 一、背景与范围

目标产品当前基于 AgentScope 构建，核心依赖以下 12 项能力：

| # | AgentScope 能力 | 核心职责 |
|---|----------------|---------|
| 1 | `ReActAgent` | Reason-Act 循环引擎 |
| 2 | `Msg` | 结构化消息（多模态内容块） |
| 3 | `TextBlock` | 文本内容块类型 |
| 4 | `Tool` (Toolkit) | 工具注册、schema 推断、执行（含流式） |
| 5 | `InMemoryMemory` | 带 mark/tag 的工作记忆 |
| 6 | `ChatModelBase` | LLM 抽象（含 stream 模式） |
| 7 | `PlanNoteBook` | 计划管理 + 工具化暴露 |
| 8 | `SubTask` | 子任务生命周期模型 |
| 9 | `TruncatedFormatterBase` | token 级截断 + tool pair 安全 |
| 10 | `Knowledge` (KnowledgeBase) | 向量语义检索 (RAG) |
| 11 | `HttpStatefulClient` | 有状态 MCP HTTP 客户端 |
| 12 | `Session` | 模块化状态持久化 |

本文档聚焦 **DARE 框架层面需要补齐的差距**，按能力逐一对比 AgentScope 实现，明确 DARE 的现状、不足和补齐方案。

---

## 二、差距分级标准

| 级别 | 含义 | 影响 |
|------|------|------|
| **F0** | 框架内核需新增接口或核心数据结构 | 影响所有使用者，需谨慎设计 |
| **F1** | 需修改现有接口或实现，有破坏性风险 | 需向后兼容设计 |
| **F2** | 现有机制可支撑，需要补充实现（无接口变更） | 改动局部，风险可控 |
| **E-only** | 仅需 Example 层适配，框架无需改动 | 零框架改动 |

---

## 三、逐能力深度差距分析

### 3.1 ReActAgent

**AgentScope 实现要点**：
- `ReActAgent.reply()` 循环：`_compress_memory_if_needed()` → `_reasoning()` → `_acting()` → repeat
- 支持 `parallel_tool_calls`（`asyncio.gather`）
- 内置 `max_iterations` 防死循环（默认 20）
- 超过 max_iterations 自动做 fallback summarization
- Hook 点：`pre/post_reasoning`、`pre/post_acting`

**DARE 现状**：
- `ReactAgent.execute()` 循环结构等价：`assemble()` → `generate()` → tool calls → repeat
- `max_tool_rounds` 防死循环（默认 10）
- Loop guard 检测重复 tool call（连续 3 次完全相同则中断）
- 支持 `plan_provider` 注入 critical_block

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| Gap-R1 | **无并行 tool 执行**：ReactAgent 串行执行 tool calls，无 `parallel_tool_calls` 选项 | F2 | P3 |
| Gap-R2 | **超时无 fallback summarization**：达到 max_tool_rounds 后直接返回错误文本，不做总结 | F2 | P4 |
| Gap-R3 | **Loop guard 过于简单**：仅检测完全相同签名的重复，不检测近似循环（如参数递增） | F2 | P5 |
| Gap-R4 | **Hook 粒度不同**：DARE Hook 在 session/milestone/plan/tool 层面，缺少 reasoning/acting 级别的 hook | F1 | P4 |
| Gap-R5 | **无自动内存压缩**：ReactAgent 循环内不会自动触发 `compress`，需外部手动调用 | F2 | P1 |

---

### 3.2 Msg (消息)

**AgentScope 实现要点**：
- `Msg(id, name, role, content, metadata, timestamp, invocation_id)`
- `content` 可以是 `str`（自动包装为 `[TextBlock]`）或 `list[ContentBlock]`
- `ContentBlock` 联合类型：`TextBlock | ThinkingBlock | ImageBlock | AudioBlock | VideoBlock | ToolUseBlock | ToolResultBlock`
- `get_text_content(sep)` 提取纯文本
- `get_content_blocks(block_type)` 按类型过滤
- 完整的 `to_dict() / from_dict()` 序列化

**DARE 现状**：
- `Message(role, content, name, metadata)` — 仅 4 个字段
- `content` 固定为 `str`，不支持结构化内容块
- 无 `id`、`timestamp` 字段
- 无 `to_dict() / from_dict()` 标准方法

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-M1** | **无 `tag`/`mark` 字段**：消息无法被标记为 reasoning/compressed/important，压缩策略无法区分消息重要性 | F0 | P1 |
| **Gap-M2** | **`content` 仅支持 `str`**：无法表示多模态内容（图片、音频等），也无法区分 TextBlock / ThinkingBlock | F0 | P5 |
| **Gap-M3** | **无 `id` 字段**：无法按 ID 引用消息，mark/delete 操作需依赖列表索引 | F0 | P2 |
| **Gap-M4** | **无 `timestamp` 字段**：无法追踪消息时间线 | F2 | P3 |
| **Gap-M5** | **无标准序列化方法**：缺少 `to_dict()`/`from_dict()`，Session 持久化依赖外部逻辑 | F2 | P2 |

---

### 3.3 TextBlock

**AgentScope 实现**：`TextBlock(type="text", text=str)` — ContentBlock 联合类型之一

**DARE 现状**：无 ContentBlock 体系，Example 层定义了 `TextBlock = TypedDict`

**差距**：与 Gap-M2 合并处理。当 Message 支持 `content_blocks` 后，TextBlock 自然成为其中一种类型。

---

### 3.4 Tool (Toolkit)

**AgentScope 实现要点**：
- `Toolkit.register_tool_function()` 支持 sync/async/partial 函数、MCP 工具
- JSON schema 从 docstring 自动推断
- `call_tool_function()` 返回 `AsyncGenerator[ToolResponse]`（流式）
- `ToolResponse` 含 `stream`、`is_last`、`is_interrupted` 标志
- 支持中间件链（onion-style），用于拦截和变换
- `ToolGroup` 分组 + 动态启用/禁用
- `preset_kwargs` 对 agent 隐藏的预设参数
- `conflict_strategy`：raise / override / skip / rename

**DARE 现状**：
- `ITool` 接口 + `ToolManager` + `ToolGateway`
- `infer_input_schema_from_execute()` 从类型注解自动推断 JSON schema
- `CapabilityDescriptor` 描述符 + `Envelope` 执行边界
- `IToolProvider` 动态提供工具
- `change_capability_status()` 启用/禁用

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| Gap-T1 | **无工具流式返回**：`ITool.execute()` 返回 `ToolResult`（单值），不支持 `AsyncGenerator` 流式结果 | F1 | P3 |
| Gap-T2 | **无中间件/拦截器链**：工具执行前后无 middleware 机制 | F2 | P4 |
| Gap-T3 | **无 `preset_kwargs`**：不能给工具预设对 agent 隐藏的参数 | F2 | P3 |
| Gap-T4 | **无冲突策略**：工具名冲突直接报错，无 override/skip/rename 选项 | F2 | P4 |

---

### 3.5 InMemoryMemory

**AgentScope 实现要点**：
- 存储结构：`list[tuple[Msg, list[str]]]` — 每条消息带 marks 列表
- `add(messages, marks=[])` 自动深拷贝、去重
- `get_memory(mark=, exclude_mark=, prepend_summary=)` 按标签过滤
- `update_messages_mark(action, mark, message_ids, filter_mark)` — add/remove/replace 标签
- `delete(ids)`、`delete_by_mark(marks)`
- `_compressed_summary: str` — 存储压缩后的摘要
- 完整 `state_dict() / load_state_dict()` 序列化

**DARE 现状**：
- `InMemorySTM`：`list[Message]`，无标签
- `add(message)`、`get(query)`、`clear()`
- `compress(max_messages)` — 按条数尾部截取
- 无 `mark()`、无按标签过滤、无 `state_dict()`

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-Mem1** | **无 mark/tag 系统**：无法标记消息为 reasoning/compressed/important，无法按标签过滤检索 | F0 | P1 |
| **Gap-Mem2** | **无 `_compressed_summary`**：压缩后的摘要无处存储，无法在 `get()` 时自动前置 | F2 | P1 |
| **Gap-Mem3** | **无 `state_dict()`/`load_state_dict()`**：STM 不可序列化，Session 持久化需外部遍历 | F2 | P2 |
| **Gap-Mem4** | **无按 ID 删除/更新**：`Message` 无 `id` 字段，无法精确操作单条消息 | F0 | P2 |
| **Gap-Mem5** | **`compress()` 不安全**：尾部截取可能孤儿化 tool call/result 对 | F2 | P1 |

---

### 3.6 ChatModelBase

**AgentScope 实现要点**：
- `ChatModelBase.__call__(messages, stream=True/False)` 返回 `ChatResponse | AsyncGenerator`
- `ChatResponse.content` 是 `list[ContentBlock]`，包含 `ThinkingBlock`
- 具体实现：OpenAI / Anthropic / Gemini / DashScope / Ollama / Trinity
- 自动解析 `reasoning_content`（DeepSeek R1 等）和 `thinking` block（Claude）

**DARE 现状**：
- `IModelAdapter.generate(model_input, options)` 返回单个 `ModelResponse`
- `ModelResponse(content=str, tool_calls, usage, metadata)` — content 是纯文本
- 具体实现：OpenAI（LangChain）/ OpenRouter（原生 openai SDK）
- **不提取 `reasoning_content`，不处理 thinking block**

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-LM1** | **`ModelResponse` 无 `thinking_content` 字段**：DeepSeek R1 的 `reasoning_content`、Claude thinking block、Qwen3 `<think>` 标签全部丢失 | F0 | **P0** |
| **Gap-LM2** | **无 `generate_stream()` 接口**：无法流式输出，UX 体验差，长任务无法观测中间过程 | F1 | P2 |
| **Gap-LM3** | **adapter 数量少**：仅 OpenAI(LangChain) + OpenRouter，缺 Anthropic/Gemini/DashScope/Ollama 原生 adapter | F2 | P3 |
| **Gap-LM4** | **Usage 不规范化 reasoning_tokens**：`usage` dict 不提取 `reasoning_tokens`，Budget 计费不准确 | F2 | P1 |

---

### 3.7 PlanNoteBook

**AgentScope 实现要点**：
- 8 个工具函数：`create_plan / view_subtasks / revise_current_plan / update_subtask_state / finish_subtask / finish_plan / view_historical_plans / recover_historical_plan`
- `Plan` 有 `state: todo/in_progress/done/abandoned`、`created_at/finished_at` 时间戳
- `PlanNotebook` 有 `plan_change_hooks` 回调
- `DefaultPlanToHint` 自动生成 `<system-hint>` 注入 context
- `max_subtasks` 限制
- 完整 `state_dict()`/`load_state_dict()` 序列化（继承 `StateModule`）
- 历史计划管理

**DARE 现状**：
- `plan_v2.Planner` 作为 `IToolProvider` 暴露 6 个工具
- `PlannerState` 有 `critical_block` 注入机制
- `Step` 无生命周期状态
- 无历史计划管理
- 无 plan_change_hooks
- 无 `state_dict()`/`load_state_dict()`

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-P1** | **`Step` 无 `status` 字段**：完成状态仅通过 `completed_step_ids` 集合追踪，无 `running/failed/skipped` | F2 | P2 |
| **Gap-P2** | **无 `finish_plan` 工具**：计划无法被显式标记为完成/放弃 | F2 | P2 |
| **Gap-P3** | **无 `revise_current_plan`**：计划创建后不可修改（`CreatePlanTool` 在 steps 非空时拒绝创建） | F2 | P2 |
| **Gap-P4** | **无历史计划管理**：`view_historical_plans/recover_historical_plan` 缺失 | F2 | P4 |
| **Gap-P5** | **无 `state_dict()` 序列化**：`PlannerState` 无法持久化到 Session | F2 | P2 |
| **Gap-P6** | **无 plan_change_hooks**：计划变更无回调通知（用于 UI 可视化等） | F2 | P4 |
| **Gap-P7** | **无 Hint 自动注入**：缺少类似 `DefaultPlanToHint` 的上下文提示生成（`critical_block` 功能类似但更简略） | F2 | P3 |

---

### 3.8 SubTask

**AgentScope 实现**：
```python
class SubTask(BaseModel):
    name, description, expected_outcome, outcome
    state: Literal["todo", "in_progress", "done", "abandoned"]
    created_at, finished_at
    finish(outcome), to_oneline_markdown(), to_markdown(detailed)
```

**DARE 现状**：`plan_v2.Step(step_id, description, params)` — 3 个字段，无生命周期

与 Gap-P1 合并处理。

---

### 3.9 TruncatedFormatterBase

**AgentScope 实现要点**：
- `format()` 循环：`_format()` → `_count()` → 超限则 `_truncate()` → repeat
- `_truncate()` 策略：保留 system，按 `tool_sequence` 和 `agent_message` 分组，从末尾逐组删除
- **tool pair 安全**：tool_use 和 tool_result 永远一起删除，API 要求不违反
- 每种 LLM provider 有独立的 formatter 子类（OpenAI/Anthropic/Gemini/...）
- 基于 **token 计数**（不是字符数），使用 `token_counter` callable

**DARE 现状**：
- `compress_context()` 三种策略（truncate/dedup/summary），全部基于**消息条数**
- **无 tool pair 安全保护**
- 无 formatter 概念（消息直接传给 adapter）
- `compress_context_llm_summary()` 做 LLM 摘要但不做安全截断
- Example 层 `CompatTruncatedFormatter` 基于**字符数**（非 token），已实现 tool pair 安全

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-F1** | **`compress_context()` 无 tool pair 安全**：截断可能孤儿化 tool call/result | F2 | **P1** |
| **Gap-F2** | **无 token 级截断**：仅支持按消息条数，不支持按 token 预算 | F2 | P2 |
| **Gap-F3** | **无 Formatter 抽象**：缺少 provider-specific 消息格式化层，所有消息以 DARE `Message` 原样传给 adapter | F1 | P3 |
| **Gap-F4** | **无自动截断触发**：需手动调用 `compress_context()`，无模型调用前自动触发机制 | F2 | P1 |

---

### 3.10 Knowledge (KnowledgeBase)

**AgentScope 实现要点**：
- `KnowledgeBase.retrieve(query, limit, score_threshold)` → `list[Document]`
- `SimpleKnowledge`：embedding model + vector store（多种后端）
- 支持文档加载器（file readers、web scrapers）
- 工具化检索：`retrieve_knowledge(query)` 注册为 tool

**DARE 现状**：
- `IKnowledge.get(query)` + `IKnowledge.add(content)`
- `RawdataKnowledge`（子串匹配）+ `VectorKnowledge`（embedding 相似度）
- 自动工具：`KnowledgeGetTool` / `KnowledgeAddTool`
- 只有 `OpenAIEmbeddingAdapter`（LangChain 依赖）

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-K1** | **缺 OpenRouter 兼容 EmbeddingAdapter**：OpenRouter 支持 embedding 模型但 DARE 无对应 adapter | F2 | P3 |
| **Gap-K2** | **`IKnowledge.get()` 是同步方法**：但底层 embedding 是 async，导致 `VectorKnowledge` 使用 `_run_async()` workaround（可能在已有 event loop 中死锁） | F1 | P2 |
| **Gap-K3** | **无文档加载器**：无 file reader/web scraper 等文档预处理管线 | F2 | P4 |
| **Gap-K4** | **无 `score_threshold` 参数**：`IKnowledge.get()` 只有 `query + **kwargs`，语义不明确 | F2 | P3 |
| **Gap-K5** | **Knowledge 无 `state_dict()`**：跨 session 无法序列化/恢复 | F2 | P3 |

---

### 3.11 HttpStatefulClient

**AgentScope 实现要点**：
- `HttpStatefulClient(name, transport, url, headers, timeout, sse_read_timeout)`
- 有状态：`connect() / close()`，`is_connected` 标志
- `list_tools()` 缓存
- `get_callable_function(name)` 返回可调用代理
- 与 `HttpStatelessClient` 共享 `MCPClientBase` 接口
- LIFO 关闭顺序要求

**DARE 现状**：
- `MCPClient + HTTPTransport`：功能等价
- Session ID 跟踪
- `MCPToolProvider` 桥接为 `ITool`
- 无上层 facade

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| Gap-H1 | **无上层 facade**：需通过 `MCPClient + HTTPTransport` 组合使用，无 `HttpStatefulClient` 等价 API | E-only | P4 |
| Gap-H2 | **无自动重连**：连接断开后不自动恢复 | F2 | P5 |
| Gap-H3 | **`list_tools()` 不缓存**：每次调用都发网络请求 | F2 | P4 |

---

### 3.12 Session

**AgentScope 实现要点**：
- `SessionBase.save_session_state(session_id, user_id, **state_modules_mapping)`
- `StateModule` 协议：`state_dict() / load_state_dict()` — 每个组件自描述序列化
- `JsonSession`：JSON 文件持久化
- `RedisSession`：Redis 持久化
- Agent 的所有子组件（memory、toolkit、plan_notebook 等）均实现 `StateModule`
- `AgentBase._AgentMeta` 自动收集 `StateModule` 属性

**DARE 现状**：
- `SessionSummary` — 审计级别的 session 摘要
- `ICheckpointStore` — 检查点存储
- **无通用 `StateModule` 协议**
- **无 `ISessionStore` 接口**
- Example 层 `JsonSessionBridge` 手动序列化 STM + notebook

**差距**：

| Gap ID | 差距 | 级别 | 优先级 |
|--------|------|------|--------|
| **Gap-S1** | **无 `StateModule` 协议**：各组件（STM、Knowledge、Planner）无统一的 `state_dict()/load_state_dict()` 接口 | F0 | P1 |
| **Gap-S2** | **无 `ISessionStore` 接口**：无标准的 session 持久化抽象（save/load 多个 StateModule） | F0 | P1 |
| **Gap-S3** | **无 `RedisSession` 后端**：仅能本地文件（需通过 Example 层 JsonSessionBridge 实现） | F2 | P4 |

---

## 四、综合差距汇总（按优先级排序）

### P0 — 阻断性（直接影响核心功能可用性）

| Gap ID | 标题 | 级别 | 所属能力 |
|--------|------|------|---------|
| Gap-LM1 | `ModelResponse` 无 `thinking_content`，thinking 模型推理内容丢失 | F0 | ChatModelBase |

### P1 — 高优先（影响迁移可行性）

| Gap ID | 标题 | 级别 | 所属能力 |
|--------|------|------|---------|
| Gap-M1 | Message 无 `tag`/`mark` 字段 | F0 | Msg |
| Gap-Mem1 | InMemorySTM 无 mark/tag 系统 | F0 | InMemoryMemory |
| Gap-Mem2 | InMemorySTM 无 `_compressed_summary` | F2 | InMemoryMemory |
| Gap-Mem5 | `compress()` 不保护 tool pair | F2 | InMemoryMemory |
| Gap-F1 | `compress_context()` 无 tool pair 安全 | F2 | TruncatedFormatter |
| Gap-F4 | 无自动截断触发机制 | F2 | TruncatedFormatter |
| Gap-R5 | ReactAgent 无自动内存压缩 | F2 | ReActAgent |
| Gap-LM4 | Usage 不规范化 reasoning_tokens | F2 | ChatModelBase |
| Gap-S1 | 无 `StateModule` 协议 | F0 | Session |
| Gap-S2 | 无 `ISessionStore` 接口 | F0 | Session |

### P2 — 中优先（影响功能完整性）

| Gap ID | 标题 | 级别 | 所属能力 |
|--------|------|------|---------|
| Gap-M3 | Message 无 `id` 字段 | F0 | Msg |
| Gap-M5 | Message 无标准序列化方法 | F2 | Msg |
| Gap-Mem3 | InMemorySTM 无 `state_dict()` | F2 | InMemoryMemory |
| Gap-Mem4 | 无按 ID 删除/更新 | F0 | InMemoryMemory |
| Gap-LM2 | 无 `generate_stream()` 接口 | F1 | ChatModelBase |
| Gap-P1 | `Step` 无 `status` 字段 | F2 | PlanNoteBook |
| Gap-P2 | 无 `finish_plan` 工具 | F2 | PlanNoteBook |
| Gap-P3 | 无 `revise_current_plan` | F2 | PlanNoteBook |
| Gap-P5 | `PlannerState` 无 `state_dict()` | F2 | PlanNoteBook |
| Gap-F2 | 无 token 级截断 | F2 | TruncatedFormatter |
| Gap-K2 | `IKnowledge.get()` 同步/异步阻抗 | F1 | Knowledge |

### P3 — 低优先

| Gap ID | 标题 | 级别 | 所属能力 |
|--------|------|------|---------|
| Gap-R1 | 无并行 tool 执行 | F2 | ReActAgent |
| Gap-M4 | Message 无 `timestamp` | F2 | Msg |
| Gap-T1 | 无工具流式返回 | F1 | Tool |
| Gap-T3 | 无 `preset_kwargs` | F2 | Tool |
| Gap-LM3 | Adapter 数量少 | F2 | ChatModelBase |
| Gap-K1 | 缺 OpenRouter EmbeddingAdapter | F2 | Knowledge |
| Gap-K4 | 无 `score_threshold` 参数 | F2 | Knowledge |
| Gap-F3 | 无 Formatter 抽象 | F1 | TruncatedFormatter |
| Gap-P7 | 无 Hint 自动注入 | F2 | PlanNoteBook |

### P4+ — 延后

| Gap ID | 标题 | 级别 |
|--------|------|------|
| Gap-R2 | 超时无 fallback summarization | F2 |
| Gap-R4 | Hook 粒度不够 | F1 |
| Gap-T2 | 无中间件/拦截器链 | F2 |
| Gap-T4 | 无工具名冲突策略 | F2 |
| Gap-P4 | 无历史计划管理 | F2 |
| Gap-P6 | 无 plan_change_hooks | F2 |
| Gap-H2 | 无自动重连 | F2 |
| Gap-H3 | `list_tools()` 不缓存 | F2 |
| Gap-K3 | 无文档加载器 | F2 |
| Gap-K5 | Knowledge 无 `state_dict()` | F2 |
| Gap-S3 | 无 RedisSession 后端 | F2 |
| Gap-M2 | content 仅 str（多模态） | F0 |
| Gap-R3 | Loop guard 过于简单 | F2 |
| Gap-H1 | 无 HttpStatefulClient facade | E-only |

---

## 五、依赖关系图

```
Gap-LM1 (thinking_content)
  └── Gap-M1 (MessageTag) ←─── Gap-Mem1 (mark system)
        └── Gap-F1 (tool_pair_safe compress)
              └── Gap-R5 (auto compress in ReactAgent)

Gap-M3 (Message.id) ←── Gap-Mem4 (delete by id)

Gap-S1 (StateModule) ←── Gap-Mem3 (STM state_dict)
                     ←── Gap-P5 (PlannerState state_dict)
                     ←── Gap-S2 (ISessionStore)

Gap-LM2 (generate_stream) ←── Gap-T1 (tool streaming)
```

---

## 六、实施路线建议

### Phase 1：核心数据模型增强（P0 + P1 核心）

1. **Gap-LM1**：`ModelResponse` 增加 `thinking_content: str | None`，两个 adapter 实现提取逻辑
2. **Gap-LM4**：`_extract_usage()` 规范化 `reasoning_tokens`
3. **Gap-M1 + Gap-M3**：`Message` 增加 `id: str`、`tag: MessageTag | None`
4. **Gap-M5**：`Message` 增加 `to_dict()`/`from_dict()`
5. **Gap-Mem1 + Gap-Mem2**：`InMemorySTM` 增加 mark 系统 + `_compressed_summary`
6. **Gap-Mem5 + Gap-F1**：`compress()` 和 `compress_context()` 增加 `tool_pair_safe` 参数

### Phase 2：Session 持久化体系（P1 Session）

7. **Gap-S1**：定义 `StateModule` 协议
8. **Gap-Mem3**：`InMemorySTM` 实现 `state_dict()`/`load_state_dict()`
9. **Gap-P5**：`PlannerState` 实现序列化
10. **Gap-S2**：定义并实现 `ISessionStore`（至少 JSON 后端）

### Phase 3：执行引擎增强（P1-P2 执行相关）

11. **Gap-R5 + Gap-F4**：ReactAgent 循环内增加自动压缩触发
12. **Gap-P1**：`Step` 增加 `status` 字段
13. **Gap-P2 + Gap-P3**：补齐 `finish_plan` 和 `revise_current_plan` 工具
14. **Gap-F2**：增加 token 级截断选项

### Phase 4：流式 + 扩展（P2-P3）

15. **Gap-LM2**：`IModelAdapter` 增加 `generate_stream()` + 默认实现
16. **Gap-K2**：`IKnowledge` 增加 `async aget()` 方法
17. **Gap-K1**：实现 `OpenRouterEmbeddingAdapter`
18. **Gap-R1**：ReactAgent 增加 `parallel_tool_calls` 选项

---

## 七、补齐方案代码草案

### Gap-LM1：thinking_content

```python
# dare_framework/model/types.py
@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    thinking_content: str | None = None   # 新增
    metadata: dict[str, Any] = field(default_factory=dict)

# dare_framework/model/adapters/openrouter_adapter.py
def _extract_content_and_thinking(message: Any) -> tuple[str, str | None]:
    """统一提取 content 和 thinking_content。"""
    # 1. reasoning_content 字段（DeepSeek R1 / GLM-4）
    reasoning = getattr(message, "reasoning_content", None)
    if isinstance(reasoning, str) and reasoning.strip():
        return (message.content or ""), reasoning
    # 2. content 为列表（Claude thinking blocks via OpenRouter）
    content_raw = message.content
    if isinstance(content_raw, list):
        text_parts, thinking_parts = [], []
        for block in content_raw:
            if isinstance(block, dict):
                if block.get("type") == "thinking":
                    thinking_parts.append(block.get("thinking", ""))
                elif block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
        return "\n".join(text_parts), "\n".join(thinking_parts) or None
    # 3. <think>...</think> 内嵌（Qwen3）
    if isinstance(content_raw, str) and "<think>" in content_raw:
        import re
        match = re.search(r"<think>(.*?)</think>", content_raw, re.DOTALL)
        if match:
            thinking = match.group(1).strip()
            text = re.sub(r"<think>.*?</think>", "", content_raw, flags=re.DOTALL).strip()
            return text, thinking or None
    return (content_raw or ""), None
```

### Gap-M1 + Gap-M3：Message 增强

```python
# dare_framework/context/types.py
from enum import Enum
import uuid

class MessageTag(str, Enum):
    REASONING   = "reasoning"
    COMPRESSED  = "compressed"
    IMPORTANT   = "important"
    TOOL_CALL   = "tool_call"
    TOOL_RESULT = "tool_result"

@dataclass
class Message:
    role: str
    content: str
    name: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tag: MessageTag | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "role": self.role, "content": self.content,
            "name": self.name, "tag": self.tag.value if self.tag else None,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        tag_val = data.get("tag")
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            name=data.get("name"),
            tag=MessageTag(tag_val) if tag_val else None,
            metadata=data.get("metadata", {}),
        )
```

### Gap-F1：tool pair 安全压缩

```python
# dare_framework/compression/core.py 增强
def _find_tool_pair_boundary(messages: list[Message], cut_index: int) -> int:
    """确保截断点不破坏 tool call/result 配对。"""
    i = cut_index
    while i < len(messages):
        msg = messages[i]
        if msg.role == "tool":
            # 向前查找对应的 assistant tool_call
            for j in range(i - 1, -1, -1):
                if messages[j].role == "assistant" and messages[j].metadata.get("tool_calls"):
                    i = j  # 将截断点前移到 assistant 消息处
                    break
            break
        if msg.role == "assistant" and msg.metadata.get("tool_calls"):
            # 需要连带后续的 tool result 一起保留
            break
        i += 1
    return i
```

### Gap-S1：StateModule 协议

```python
# dare_framework/session/kernel.py（新文件）
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class StateModule(Protocol):
    def state_dict(self) -> dict[str, Any]: ...
    def load_state_dict(self, state: dict[str, Any]) -> None: ...

class ISessionStore(Protocol):
    async def save(self, session_id: str, user_id: str = "",
                   **modules: StateModule) -> None: ...
    async def load(self, session_id: str, user_id: str = "",
                   allow_not_exist: bool = True,
                   **modules: StateModule) -> None: ...
```

---

## 八、Example 10 与本文档的关系

```
本文档（agentscope-migration-framework-gaps.md）
  ├── 12 项能力逐一对比分析
  ├── 40+ 个具体 Gap（含 ID、级别、优先级）
  ├── 依赖关系图
  ├── 分 Phase 实施路线
  └── 关键 Gap 的代码草案

Example 10 DESIGN.md
  ├── 能力差异矩阵（Example 视角）
  └── 指向本文档（框架补齐视角）

Example 10 compat_agent.py
  ├── 过渡性 shim（CompatMsg / CompatTruncatedFormatter / ...）
  ├── Gap stub 声明（标注待框架补齐的能力）
  └── 完整可运行的兼容 agent demo
```

---

## 九、已排除的差距（有意不追踪）

| 能力 | 原因 |
|------|------|
| AgentScope `AgentBase._AgentMeta` 自动收集 | DARE 架构不依赖 metaclass，可通过 builder 模式替代 |
| AgentScope `RedisMemory / SQLAlchemyMemory` | DARE 有 LTM 后端，短期内不需要替换 STM 后端 |
| AgentScope `TrinityModel`（RL 训练集成） | 不在目标产品范围内 |
