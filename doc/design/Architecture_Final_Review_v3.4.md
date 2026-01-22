# DARE Framework 架构终稿评审 v3.4（Final）

> **状态**：Final（以代码为准）  
> **范围**：仅覆盖 `dare_framework3_4/`（v3.4 最小集）  
> **最后对齐**：以仓库中 `dare_framework3_4/` 当前实现为权威

---

## 0. 读者须知（最重要）

1. **设计文档与代码必须完全一致**：本文件描述的“已实现（Implemented）”内容，必须在 `dare_framework3_4/` 中能找到一一对应的代码实现。
2. **允许“预留（Reserved）”**：如果本文档描述了某能力，但当前代码尚未实现，必须明确标注为 **Reserved**，并说明未来拟落位的代码位置（但不得冒充已实现）。
3. **v3.4 的定位是“最小可用的 Context-centric 架构骨架”**：只保留 Context/Memory/Model/Tool(仅 listing)/Agent 的最小闭环，复杂 Plan/Orchestrator/ToolLoop 等不在 v3.4 最小集内。

---

## 1. 设计目标与非目标

### 1.1 设计目标（Goals）

- **Context-centric**：以 `Context` 作为核心实体，持有短期记忆（STM）、预算（Budget）、以及外部检索源引用（LTM/Knowledge）。
- **按需组装**：每次调用模型前通过 `Context.assemble()` 生成一次性请求上下文（`AssembledContext`）。
- **最小可运行闭环**：提供一个最小的可运行 Agent（`SimpleChatAgent`）+ 一个可用的模型适配器（`OpenAIModelAdapter`）+ 一个默认 STM（`InMemorySTM`）。
- **可插拔扩展点**：以 Protocol/接口方式暴露可替换组件（Memory/Knowledge/ToolProvider/ModelAdapter）。

### 1.2 非目标（Non-Goals）

- 不在 v3.4 最小集内实现：Plan/Execute/Tool loop、网关校验、复杂预算归因、事件日志、可恢复执行控制、MCP 全链路等（这些内容可在后续版本中扩展）。
- 不在 v3.4 最小集内实现：将 tools 以 system prompt catalog 注入并进行裁剪/消歧的完整“上下文工程 Layer 3”流程（当前只提供 `tools` 列表字段，供模型适配器绑定）。

---

## 2. 目录结构与“设计 ↔ 代码”映射（1:1）

> 本节是“对齐清单”。任何改动请优先更新此表，确保文档与代码同步。

### 2.1 包结构

```
dare_framework3_4/
├── __init__.py
├── agent/
│   ├── base.py
│   └── simple_chat.py
├── context/
│   └── context.py
├── memory/
│   ├── component.py
│   └── internal/in_memory_stm.py
├── knowledge/
│   └── component.py
├── model/
│   ├── component.py
│   ├── types.py
│   └── internal/openai_adapter.py
└── tool/
    ├── component.py
    └── types.py
```

### 2.2 核心组件映射表

| 领域 | 设计对象 | 代码位置 | 状态 |
|---|---|---|---|
| Version | v3.4 版本号 | `dare_framework3_4/__init__.py` | Implemented |
| Context | `Message`/`Budget`/`AssembledContext`/`IRetrievalContext`/`IContext`/`Context` | `dare_framework3_4/context/context.py` | Implemented |
| Agent | `BaseAgent`/`SimpleChatAgent` | `dare_framework3_4/agent/base.py` / `dare_framework3_4/agent/simple_chat.py` | Implemented |
| Memory | `IShortTermMemory`/`ILongTermMemory`/`InMemorySTM` | `dare_framework3_4/memory/component.py` / `dare_framework3_4/memory/internal/in_memory_stm.py` | Implemented（LTM 仅接口） |
| Knowledge | `IKnowledge` | `dare_framework3_4/knowledge/component.py` | Implemented（仅接口） |
| Model | `IModelAdapter`/`Prompt`/`ModelResponse`/`GenerateOptions`/`OpenAIModelAdapter` | `dare_framework3_4/model/*` | Implemented |
| Tool | `IToolProvider`/`ToolResult`/`Evidence` | `dare_framework3_4/tool/*` | Implemented（仅 listing + types） |
| Tool Internal | 工具执行实现包（预留） | `dare_framework3_4/tool/internal/` | Reserved |

---

## 3. 核心数据结构（Types）

> 所有字段以代码定义为准；本节仅做“设计解释 + 对齐点”。

### 3.1 Message（统一消息结构）

- **代码**：`dare_framework3_4/context/context.py`
- **定义**：`Message(role, content, name=None, metadata={})`
- **字段**
  - `role: str`：`system | user | assistant | tool`
  - `content: str`：消息内容
  - `name: str | None`：预留字段（当前主要用于 tool 消息的标识/关联，语义在后续版本可收敛为 tool name 或 tool_call_id）
  - `metadata: dict[str, Any]`：扩展字段（追踪、归因、tool_calls 等）

**说明（与当前实现对齐）**
- v3.4 最小集中，`Message` 不强制内建 `tool_calls/tool_call_id` 字段；需要携带额外信息时，统一放在 `metadata` 中。

### 3.2 Budget（预算 + 使用量）

- **代码**：`dare_framework3_4/context/context.py`
- **定义**：`Budget(max_*, used_*)`

**限制（Limits）**
- `max_tokens: int | None`
- `max_cost: float | None`
- `max_time_seconds: int | None`
- `max_tool_calls: int | None`

**使用量（Usage tracking）**
- `used_tokens: float`
- `used_cost: float`
- `used_time_seconds: float`
- `used_tool_calls: int`

### 3.3 AssembledContext（单次模型调用的“请求时上下文”）

- **代码**：`dare_framework3_4/context/context.py`
- **字段**
  - `messages: list[Message]`
  - `tools: list[dict[str, Any]]`：由 `IToolProvider.list_tools()` 提供的工具定义（LLM 兼容格式）
  - `metadata: dict[str, Any]`：例如 `context_id`

### 3.4 Prompt / ModelResponse / GenerateOptions（模型域类型）

- **代码**：`dare_framework3_4/model/types.py`

**Prompt**
- `messages: list[Message]`
- `tools: list[dict[str, Any]]`
- `metadata: dict[str, Any]`

**ModelResponse**
- `content: str`
- `tool_calls: list[dict[str, Any]]`
- `usage: dict[str, Any] | None`
- `metadata: dict[str, Any]`

**GenerateOptions**
- `temperature / max_tokens / top_p / stop / metadata`

### 3.5 ToolResult / Evidence（工具结果与证据）

- **代码**：`dare_framework3_4/tool/types.py`

**Evidence**
- `evidence_id: str`
- `kind: str`
- `payload: Any`
- `created_at: float`

**ToolResult**
- `success: bool`
- `output: dict[str, Any]`
- `error: str | None`
- `evidence: list[Evidence]`

---

## 4. 核心接口（Protocols / Contracts）

### 4.1 IRetrievalContext（统一检索接口）

- **代码**：`dare_framework3_4/context/context.py`
- **签名**：`get(self, query: str = "", **kwargs) -> list[Message]`

**设计含义**
- 统一 Memory / Knowledge 的“输出形态”为 `list[Message]`，避免上层在不同检索源之间做结构转换。

### 4.2 IContext / Context（核心 Context 实体）

- **代码**：`dare_framework3_4/context/context.py`

**字段（Fields）**
- `id: str`
- `budget: Budget`
- `config: dict[str, Any] | None`
- `short_term_memory: IRetrievalContext`（缺省为 `InMemorySTM`）
- `long_term_memory: IRetrievalContext | None`（预留引用）
- `knowledge: IRetrievalContext | None`（预留引用）
- `toollist: list[dict[str, Any]] | None`（缓存）

**方法（Methods）**
- STM：`stm_add / stm_get / stm_clear`
- Budget：`budget_use / budget_check / budget_remaining`
- Tools：`listing_tools`
- Assembly：`assemble(**options) -> AssembledContext`
- Config：`config_update(patch)`

### 4.3 Memory：IShortTermMemory / ILongTermMemory

- **代码**：`dare_framework3_4/memory/component.py`

**IShortTermMemory（STM）**
- 在 `IRetrievalContext` 基础上增加 `add/clear/compress`

**ILongTermMemory（LTM，预留接口）**
- `get(query: str, **kwargs) -> list[Message]`
- `persist(messages: list[Message]) -> None`（async）

### 4.4 Knowledge：IKnowledge（预留接口）

- **代码**：`dare_framework3_4/knowledge/component.py`
- `get(query: str, **kwargs) -> list[Message]`

### 4.5 Tool：IToolProvider（仅工具列表）

- **代码**：`dare_framework3_4/tool/component.py`
- `list_tools() -> list[dict[str, Any]]`

> 说明：v3.4 最小集只定义“工具定义如何提供给模型”，不定义“工具如何被执行”。

### 4.6 Model：IModelAdapter（模型调用契约）

- **代码**：`dare_framework3_4/model/component.py`
- `generate(prompt: Prompt, *, options: GenerateOptions | None = None) -> ModelResponse`（async）

---

## 5. 默认实现（Implementations）

### 5.1 Context（默认实现）

- **代码**：`dare_framework3_4/context/context.py`
- **默认行为**
  - 若未传入 `short_term_memory`，在 `__post_init__` 中创建 `InMemorySTM`
  - `assemble()` 当前实现：直接返回 `stm_get()` 的消息 + `listing_tools()` 的工具列表

### 5.2 InMemorySTM（默认短期记忆）

- **代码**：`dare_framework3_4/memory/internal/in_memory_stm.py`
- **行为**
  - 内存数组存储消息
  - `compress(max_messages)`：仅保留最近 N 条消息（用于未来的上下文窗口控制）

### 5.3 SimpleChatAgent（最小可运行 Agent）

- **代码**：`dare_framework3_4/agent/simple_chat.py`
- **运行流（单轮）**
  1. `stm_add(user_message)`
  2. `assembled = context.assemble()`
  3. `prompt = Prompt(messages=assembled.messages, tools=assembled.tools, metadata=assembled.metadata)`
  4. `response = await model.generate(prompt)`
  5. `stm_add(assistant_message)`
  6. 若 `response.usage.total_tokens` 存在：`budget_use("tokens", tokens)`
  7. `budget_check()`

### 5.4 OpenAIModelAdapter（OpenAI-compatible 适配器）

- **代码**：`dare_framework3_4/model/internal/openai_adapter.py`
- **依赖**
  - 运行时可选：`langchain-openai`, `langchain-core`
  - 可选：`httpx`（用于自定义 HTTP client options）
- **关键行为**
  - 将 `Prompt.messages` 映射到 LangChain message（System/Human/AI/Tool）
  - 将 `Prompt.tools` 转换为 OpenAI function tool 格式并 `bind_tools`
  - 从模型返回中抽取 `tool_calls` 与 `usage`

---

## 6. 端到端最小运行链路（Example）

- **示例代码**：`examples/basic-chat/chat3.4.py`
- **最小依赖**：
  - 一个 `IModelAdapter` 实现（例如 `OpenAIModelAdapter`）
  - v3.4 默认 `Context`（自动提供 `InMemorySTM`）

---

## 7. 扩展点（Extension Points）

> v3.4 的扩展以“组合/注入”为主，而不是继承大一统基类。

### 7.1 替换/增强短期记忆（STM）

- 实现 `IShortTermMemory` 并注入到 `Context(short_term_memory=...)`

### 7.2 接入长期记忆（LTM，预留）

- 实现 `ILongTermMemory` 并注入 `Context(long_term_memory=...)`
- 当前 `Context.assemble()` 尚未默认拉取 LTM；如需合并检索结果，可自定义 `assemble()` 策略（见 7.4）

### 7.3 接入知识检索（Knowledge，预留）

- 实现 `IKnowledge` 并注入 `Context(knowledge=...)`
- 当前 `Context.assemble()` 尚未默认拉取 Knowledge；同样建议自定义 `assemble()` 策略

### 7.4 自定义上下文组装（Assembly）

- 方式：覆写 `Context.assemble()`（或在未来版本中抽出独立 Assembly 组件）
- 典型策略（Reserved）
  - tools catalog 注入为 system message
  - LTM/Knowledge/STM 的合并顺序与去重
  - 在预算约束下做裁剪/压缩（与 `IShortTermMemory.compress` 协同）

### 7.5 提供工具定义（Tool listing）

- 实现 `IToolProvider.list_tools()` 并挂载到 `Context`（当前通过 `_tool_provider` 注入）

---

## 8. 预留能力清单（Reserved）

> 本节用于“设计先行但代码未实现”的预留；不允许写成已实现。

### 8.1 Tool 执行链路（Tool Gateway / Tool Loop）

- **状态**：Reserved（v3.4 最小集不实现）
- **拟落位**：`dare_framework3_4/tool/internal/`（未来补齐）
- **预期内容**
  - Tool 抽象（ITool）
  - ToolGateway（invoke）
  - 运行态上下文与执行控制（ExecutionControl）
  - MCP 工具适配（MCPAdapter）

### 8.2 Message 的 tool_call schema 收敛

- **状态**：Reserved
- **问题**：当前 `Message.name/metadata` 可承载 tool 相关信息，但 schema 未固化
- **方向**：未来可将 `tool_call_id/tool_calls` 作为 `Message` 的显式字段，减少约定分散

---

## 9. 变更规则（维护本设计的约束）

1. 修改 `dare_framework3_4/` 的 public API（`__init__.py` 导出）时，必须同步更新本文档的“映射表/类型/接口”章节。
2. 新增“Reserved”能力时，必须写清楚 **状态** 与 **拟落位代码路径**，并避免对行为做过度承诺。
3. 如果实现落地导致 Reserved → Implemented，应同时：
   - 更新本文档状态
   - 增加最小可运行示例或测试（若项目当前约束允许）

