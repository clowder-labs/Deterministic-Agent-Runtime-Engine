# Context 与 STM/LTM/Knowledge 深度联动：详细实现计划

> 参考 **AgentScope** 的 Memory / LongTermMemory / KnowledgeBase / 压缩 设计与 ReActAgent.reply() 流程，在 DARE 中把 Context 做成真正的「上下文中枢」，与 STM、LTM、Knowledge 形成可配置、可扩展的联动。**方案在术语、接口签名、单轮流程、配置项上与 AgentScope 对齐**，便于实现时直接参照；详见第 8 节。本文档为**方案与计划**，不直接写代码。

---

## 1. 现状与目标

### 1.1 当前 DARE 的不足

| 维度 | 现状 | 期望 |
|------|------|------|
| **assemble** | 仅 `stm_get()` 全量 + tools + sys_prompt + skill | 按策略从 STM/LTM/Knowledge 取数、排序、控 token，再组装 |
| **LTM** | Context 持有引用，assemble 不调用 | 在 assemble 或「每轮开始」按 query 检索，结果注入上下文 |
| **Knowledge** | 仅通过 knowledge_get/knowledge_add 工具写回 STM | 除工具路径外，支持「每轮开始」自动 RAG 注入 |
| **检索语义** | `IRetrievalContext.get(query, **kwargs)` 存在但未用 | 明确 query 来源、传入策略，供 LTM/Knowledge 使用 |
| **压缩** | 简单委托 STM.compress，策略单一 | 与 assemble 策略协同：marks、摘要前置、trigger 条件 |

### 1.2 AgentScope 可借鉴点（简要）

- **检索时机**：每轮 `reply()` 开始先做 LTM 检索、再 RAG 检索，结果**作为 Msg 写入 memory**，再进入 reasoning 循环；即「先 enrichment，再 format([sys_prompt, *memory.get_memory()])」。
- **LTM 模式**：`long_term_memory_mode`: `"static_control"` | `"agent_control"` | `"both"`；static 下每轮开始 retrieve、结束 record；agent 下通过工具 `record_to_memory` / `retrieve_from_memory`。
- **Knowledge**：支持 `list[KnowledgeBase]`；用最后一条 user 消息做 query；可选 **enable_rewrite_query**（LLM 改写后再检索）；检索结果按 score 排序，包成 `<retrieved_knowledge>...</retrieved_knowledge>` 的 Msg 写入 memory。
- **Memory（STM）**：`add(memories, marks)`、`get_memory(mark, exclude_mark, prepend_summary)`、`delete_by_mark`、`update_messages_mark`、`update_compressed_summary`；marks：`hint`（用后删除）、`compressed`（已压缩）。
- **压缩**：`CompressionConfig`：`enable`、`trigger_threshold`（token 数）、`keep_recent`（默认 3）、结构化 `summary_schema`（task_overview / current_state / important_discoveries / next_steps / context_to_preserve）、`summary_template`、可选 `compression_model`；摘要**前置**到 get_memory() 返回列表；压缩时保证 tool_use/tool_result 成对保留。

---

## 2. 总体架构：Context 为中枢 + 组装策略可插拔

### 2.1 核心思路

- **Context** 仍持有 STM、LTM、Knowledge、Budget、Tools、Prompt 等引用。
- **assemble** 的「消息从哪来、怎么排、多少 token」交给 **IContextAssemblyStrategy**（或命名如 `IAssemblyStrategy`）完成；Context.assemble() 只负责：取策略、调用策略、用策略返回的 messages 与现有 tools/sys_prompt 拼成 AssembledContext。
- **当前 query**：由「最后一条 user 消息」或 Task/Context 槽位提供，传入策略，供 LTM/Knowledge 检索使用。
- **默认策略**：行为与当前完全一致（仅 STM 全量），保证兼容。

### 2.2 与 STM/LTM/Knowledge 的联动方式（两种可选模式）

- **模式 A（AgentScope 式）**：在「每轮开始」或「assemble 前」先做 LTM/Knowledge 检索，将结果**作为带标记的 Message 写入 STM**，然后 assemble 只从 STM 取消息（STM 已含 LTM/Knowledge 注入）。  
  - 优点：assemble 逻辑简单，仅「STM + tools + prompt」；压缩、marks 都作用在同一 STM 上。  
  - 缺点：LTM/Knowledge 结果会持久留在 STM，需通过 **marks** 区分并在需要时排除或单独清理。

- **模式 B（纯 assemble 内检索）**：assemble 时策略内部分别调 STM.get()、LTM.get(query)、Knowledge.get(query)，在策略内合并、排序、截断后返回 messages，**不写回 STM**。  
  - 优点：LTM/Knowledge 不污染 STM，语义清晰。  
  - 缺点：每次 assemble 都要检索；若需「检索结果参与下一轮压缩」要额外设计。

**建议**：先采用 **模式 A** 为主（与 AgentScope 一致，实现路径清晰），在策略中明确「enrichment 阶段」：在 assemble 前由策略或 Context 执行「取 query → LTM 检索 → Knowledge 检索 → 结果以带 source 标记的 Message 写入 STM」，然后 assemble 只做 STM + tools + prompt。这样「联动」体现在：**谁在何时往 STM 里写什么**，以及 **STM.get(mark=..., exclude_mark=..., prepend_summary=...)** 的约定。

### 2.3 STM / LTM / Knowledge / Context 各自「存什么」与「谁在何时写入」

四个概念里，**只有 STM、LTM、Knowledge 是真正的“存储器”**；Context 本身不存对话或知识内容，只存**引用和运行时状态**。下面分组件说明「放什么信息」和「存的逻辑」。

---

#### Context（上下文聚合器，本身不存对话/知识）

| 项目 | 说明 |
|------|------|
| **放什么** | 不存放具体对话或知识内容。存放的是：对 STM / LTM / Knowledge 的**引用**、Budget（用量与上限）、当前 sys_prompt、当前 skill、tool 列表来源（如 ToolManager）、可选 config 快照、可选「当前 query」槽位。 |
| **谁写入** | Builder 在构建时注入 STM/LTM/Knowledge 引用、ToolProvider、sys_prompt；Agent 或 Planner 在运行时可设置 current_query；Budget 由 Agent 在每次用 token/成本/工具调用后更新。 |
| **存的逻辑** | 无“存储内容”的逻辑，只有“持有引用 + 在 assemble 时按策略从 STM（及通过 enrichment 写入 STM 的 LTM/Knowledge 结果）取数并拼成 AssembledContext”。 |

总结：Context 是**聚合器与入口**，不负责持久化任何对话或知识；真正的“存”发生在 STM、LTM、Knowledge 三个存储上。

---

#### STM（短期记忆：当前会话的对话与本轮注入的检索结果）

| 项目 | 说明 |
|------|------|
| **放什么** | 当前**会话内**的消息序列：用户输入、助手回复、工具调用、工具结果；以及（在模式 A 下）本轮或之前轮次**注入进来的** LTM 检索结果、Knowledge 检索结果（以 Message 形式，带 source/ mark）。压缩后还可能多出：摘要文本（_compressed_summary）、被折叠消息的 mark（compressed）。 |
| **谁写入** | **Agent/编排层**：用户消息入参时 `stm_add(user_msg)`；模型返回后 `stm_add(assistant_msg)`；工具执行后 `stm_add(tool_result_msg)`。**组装策略/Enrichment**：在 assemble 前把 LTM/Knowledge 检索结果写成 Message 写入 STM（带 source=ltm 或 knowledge，可选 mark）。**压缩**：compress() 时可能更新 STM 内消息的 mark（如打上 compressed）、并写入或更新 _compressed_summary。 |
| **存的逻辑** | 按**时间顺序**追加（append）；不跨会话持久化，会话结束或清空时 STM 可被 clear。写入频率高（每轮多次），生命周期 = 单次 run 或单会话。 |

总结：STM = 本会话的“对话流” + 本轮为服务模型而注入的 LTM/Knowledge 片段；**只有 STM 会直接收到“对话消息”和“检索结果消息”的写入**。

---

#### STM 为何会“又放对话又放检索”？——职责边界与可选拆分

**为何会混在一起（模式 A）**  
- 实现简单：assemble 时**只从一个地方取**——“当前要喂给模型的全部消息”都在 STM 里，一次 `stm.get()` 即可，压缩、截断、marks 也只维护一套。  
- 与 AgentScope 一致：检索结果以「用户侧提示」的形式插入对话流（`<long_term_memory>...</long_term_memory>`、`<retrieved_knowledge>...</retrieved_knowledge>`），模型看到的就是一条条 Message，不区分“来自对话”还是“来自检索”。

**如何理清边界（不改实现也能说清）**  
- 把 STM 理解为：**本会话的「上下文窗口暂存区」**，里面有两类内容，用 **source / mark** 严格区分：  
  - **对话流**：`source="stm"` 或不设 source；用户/助手/工具消息，按时间顺序 append，是“主序列”。  
  - **检索注入**：`source="ltm"` 或 `source="knowledge"`，mark 如 `ltm_injected` / `knowledge_injected`；只在 enrichment 时写入，**不参与“对话历史”的语义**，只是“为本轮模型看的补充材料”。  
- 策略约定：例如「每轮 assemble 前清掉上轮的 ltm_injected / knowledge_injected」，这样检索结果**不会在 STM 里堆积**，只是“当轮有效”；或选择保留多轮，由配置决定。  
- 这样**概念上**仍是“STM 里有两类东西”，但**职责清晰**：对话 = 会话状态；检索注入 = 当轮附带的 RAG/LTM 片段，生命周期可单独约定。

**可选方案：STM 只放对话，检索单独放（双缓冲）**  
若希望 **STM 只存多轮对话**、检索结果不写进 STM，可采用「双缓冲」：

- **对话缓冲（STM）**：只存用户/助手/工具消息；只由 Agent 写入；compress 只作用于此。  
- **注入缓冲（EnrichmentBuffer / RetrievalBuffer）**：只存本轮 LTM/Knowledge 检索结果（Message 列表）；enrichment 时写入，**不写入 STM**；assemble 时策略做：`messages = stm.get(...) + enrichment_buffer.get()`（或按顺序/位置合并），再返回。  
- 这样 **STM 职责单一**：“当前会话的对话序列”；检索结果“仅当轮有效”，用完即弃或由 EnrichmentBuffer 在每轮开始时清空。  
- 代价：assemble 要合并两个来源；压缩若只压 STM，注入缓冲不参与压缩（通常注入量小，可接受）；需要多维护一个 buffer 的生命周期（何时清空）。

**建议**  
- 若优先**实现简单、与现有 AgentScope 一致**：保留模式 A，在文档与命名上明确“STM = 对话流 + 当轮检索注入，用 source/mark 区分；注入可每轮清理”。  
- 若优先**概念干净、STM 只做对话**：采用双缓冲，STM 只放对话，检索结果放进 EnrichmentBuffer，assemble 时再合并。

---

#### LTM（长期记忆：跨会话的持久化信息）

| 项目 | 说明 |
|------|------|
| **放什么** | **跨会话**保留的信息：可以是“从历史会话中提炼的事实、经历、用户偏好”等，具体形态依赖实现（例如原始 Message 的持久化、或嵌入后的向量 + 元数据、或结构化记录）。与 STM 的区别：LTM 是**持久存储**，会话结束后仍然存在。 |
| **谁写入** | **static_control 模式**：由**系统**在每轮回复**结束时**自动把本轮的对话（或过滤后的子集）写入 LTM，例如 `ltm.record(msgs)`，msgs 通常来自当前 STM 的快照（如 exclude_mark=compressed 的原始对话）。**agent_control 模式**：由**模型通过工具**主动调用“记录到长期记忆”的工具（如 record_to_memory(thinking, content)），工具内部调 LTM 的写接口。**both**：两种写入路径并存。 |
| **存的逻辑** | **写少读多**：写入发生在“轮次结束”或“模型主动记一笔”；读取发生在每轮开始或 assemble 前（retrieve(query)），用于丰富当前上下文。存储层可做去重、摘要、嵌入等，取决于 LTM 实现（rawdata / vector 等）。 |

总结：LTM = 跨会话的“记忆库”；**存的是从会话中沉淀下来的内容**，要么系统按轮自动存（static），要么模型通过工具按需存（agent）。

---

#### Knowledge（知识库：领域文档/参考材料）

| 项目 | 说明 |
|------|------|
| **放什么** | **与对话无关**的参考材料：文档、说明、FAQ、代码片段等。通常以“文档 → 分块 → 向量/索引”的形式存在；检索时按 query 返回相关片段（带 score）。不存“谁说了什么”的对话，只存“有什么知识”。 |
| **谁写入** | **构建/运维时**：通过 knowledge_add 工具或离线脚本把文档/文本写入知识库（嵌入 + 存入向量库或 rawdata 存储）。**运行时**：模型可调用 knowledge_add 类工具往知识库里追加内容（若实现支持）；但多数场景下 Knowledge 是**预先灌入、相对静态**的。 |
| **存的逻辑** | **写少读多**，且写入与“对话轮次”无必然关系；写入的是“知识条目”，不是“本轮对话”。检索结果**不写回 Knowledge**，而是按模式 A 写进 STM，供本轮模型使用。 |

总结：Knowledge = 外部知识源；**存的是文档/知识本身**，不存会话；会话里用到的是“检索出来的副本”，以 Message 形式放进 STM。

---

#### 数据流小结（存与取）

```
写入（存）：
  用户/助手/工具消息  ──→  STM（每轮多次）
  LTM 检索结果        ──→  STM（enrichment，每轮开始前）
  Knowledge 检索结果  ──→  STM（enrichment，每轮开始前）
  本轮 STM 快照      ──→  LTM（每轮结束，static_control）
  模型调用 record_to_memory ──→  LTM（agent_control）
  文档/知识录入      ──→  Knowledge（构建时或工具 knowledge_add）

读取（取）：
  assemble 时        ←──  STM（get，含压缩摘要与 marks）
  LTM.retrieve(query) ←──  当前 query（enrichment 时）
  Knowledge.get(query) ←──  当前 query（enrichment 时）
```

因此：**“存”只发生在 STM（对话+注入）、LTM（跨会话记忆）、Knowledge（知识条目）**；Context 只做引用与组装，不存这些内容本身。

---

#### 写入的触发方式：框架代码 vs 模型 Function/Tool 调用

“谁在什么时候往 STM/LTM/Knowledge 写”有两种触发方式：**框架/编排层直接调用**（代码里调 API），和**模型的 function call / tool 调用**（模型决定要记/要加，通过工具执行写操作）。下表分开说明。

| 写入目标 | 触发方式 | 说明 |
|----------|----------|------|
| **STM（用户/助手/工具消息）** | **框架代码** | Agent 在收到用户输入后调 `stm_add(user_msg)`；模型返回后调 `stm_add(assistant_msg)`；工具执行后调 `stm_add(tool_result_msg)`。**不经过模型的 function call**。 |
| **STM（LTM/Knowledge 检索注入）** | **框架代码** | Enrichment 阶段（策略或 Context）在 assemble 前调 LTM/Knowledge 的 get，再把结果转成 Message 调 `stm_add(...)`。**不经过模型的 function call**。 |
| **LTM（每轮结束自动记）** | **框架代码** | static_control 下，每轮回复**结束时** Agent 调 `ltm.record(msgs)`，msgs 来自当前 STM。**不经过模型的 function call**。 |
| **LTM（模型主动记一笔）** | **模型的 tool 调用** | agent_control 下，模型通过工具 `record_to_memory(thinking, content)` 主动记；**工具实现内部**调 LTM 的写接口。**由 function call 触发**。 |
| **LTM（检索结果写回 STM）** | **框架代码** | retrieve 后由策略/Context 把结果写进 STM，见上。不涉及 LTM 的“写”，只是读 LTM 再写 STM。 |
| **Knowledge（构建/灌库）** | **脚本或 API** | 离线或运维时通过 `knowledge.add_documents` / 脚本写入，一般不经过模型。 |
| **Knowledge（模型主动加一条）** | **模型的 tool 调用** | 若提供 `knowledge_add` 工具，模型可调该工具往知识库追加内容；**工具实现内部**调 Knowledge 的 add。**由 function call 触发**。 |

**小结**  
- **STM 的写入**：全部由**框架代码**完成（用户/助手/工具消息 + enrichment 注入），**不通过模型的 function call**。  
- **LTM 的写入**：**static_control** = 框架在每轮结束调 `ltm.record`；**agent_control** = 模型的 `record_to_memory` **tool 调用**触发写入。  
- **Knowledge 的写入**：通常由**脚本/API**灌库；若开放 `knowledge_add` 工具，则**模型的 tool 调用**也可触发写入。  

因此：**只有“模型主动记 LTM”和“模型主动加 Knowledge”这两类写是由 function call 完成的**；其余（STM 全部、LTM 的自动 record）都是框架/编排层在代码里直接调用写入接口完成。

---

## 3. 数据与接口层面的细节

### 3.1 当前 query 的获取与传入

- **来源（优先级可配置）**：  
  1. Context 上的显式槽位，例如 `context.set_current_query(str)`（由 Planner/Agent 在 assemble 前设置）。  
  2. Task 上的字段，如 `Task.query` 或 `Task.summary`。  
  3. 从 STM 最后一条 role=user 的 Message 的 content 抽取（兼容现有无 Task 的 ReAct）。  
- **传入策略**：`assemble(query=..., **options)` 或 `options["query"]`；若未提供，策略内部可从 Context 只读视图（如最近一条 user message）推导。

### 3.2 Message 来源标记（source / role 约定）

- 检索结果若写入 STM，建议统一用 **metadata.source**（或 role + name）区分来源，便于策略与观测：  
  - `source="stm"`：普通对话消息。  
  - `source="ltm"`：来自长期记忆检索。  
  - `source="knowledge"`：来自知识库检索。  
- 内容包裹格式（与 AgentScope 对齐，便于模型理解）：  
  - LTM：如 `<long_term_memory>...</long_term_memory>` 的 user 消息。  
  - Knowledge：如 `<retrieved_knowledge>...</retrieved_knowledge>` 的 user 消息。  
- 这样 assemble 时若需要「只取对话、不取 hint」可依赖 mark；若需要「区分来源做排序」可用 metadata.source。

### 3.3 STM 的 marks 与 get 语义

- **扩展 IShortTermMemory.get**（或通过适配层）：支持 `get(query="", mark=None, exclude_mark=None, prepend_summary=False, **kwargs) -> list[Message]`。  
  - **mark / exclude_mark**：与 AgentScope 一致，用于过滤（如排除已压缩块、仅取某类 hint）。  
  - **prepend_summary**：若为 True 且 STM 维护了 `_compressed_summary`，则在返回列表前插入一条「摘要」Message（如 role=user，content=摘要文本）。  
- **Marks 约定**（与压缩、enrichment 协同）：  
  - `hint`：一次性提示，用后可由调用方 delete_by_mark("hint")。  
  - `compressed`：已被压缩为摘要的旧消息，get 时可通过 exclude_mark="compressed" 不参与「原始消息」列表（摘要通过 prepend_summary 提供）。  
  - 可选：`ltm_injected` / `knowledge_injected`：标记本轮注入的 LTM/Knowledge 消息，便于「仅在本轮有效、下轮可清」等策略。

### 3.4 LTM 的「静态/代理」模式（与 AgentScope 对齐）

- **static_control**：  
  - 每轮「开始」：调用 **`ltm.retrieve(msg_or_query, limit=5, **kwargs)`**；**与 AgentScope 一致：retrieve 返回 str**（拼好的文本），将该 str 包成一条 Message（如 `<long_term_memory>...</long_term_memory>`）写入 STM。  
  - 每轮「结束」：将本轮 STM 内容（如 exclude_mark=compressed）调用 **`ltm.record(msgs)`** 持久化（AgentScope：`record(msgs: list[Msg | None])`）。  
- **agent_control**：仅通过工具 **`record_to_memory(thinking, content: list[str])`** / **`retrieve_from_memory(keywords: list[str], limit=5)`** 由模型决定何时记、何时取；不在 assemble 前自动注入。  
- **both**：同时开启上述两种。  
- 在 DARE 中由 **assembly.ltm_mode**（或 long_term_memory_mode）配置；Strategy 在 enrichment 阶段仅当 static_control 时执行 LTM.retrieve 并将结果写 STM。

### 3.5 Knowledge（RAG）的检索与注入

- **query**：与 LTM 共用同一「当前 query」来源；可选 **query_rewrite**：在检索前用 LLM 将用户句改写为更具体的检索 query（如 AgentScope 的 enable_rewrite_query）。  
- **检索**：`knowledge.get(query, limit=5, score_threshold=..., **kwargs)`，返回 list  of 带 score 的条目（可映射为 Message 或统一 RetrievalResult 类型）。  
- **排序**：按 score 降序；可选 rerank。  
- **注入**：将结果拼成一段文本，包在 `<retrieved_knowledge>...</retrieved_knowledge>` 中，作为一条 Message（如 role=user，name="knowledge"）写入 STM；metadata.source="knowledge"。  
- **与工具并存**：保留现有 knowledge_get / knowledge_add 工具；「每轮自动 RAG」与「模型按需调用工具」可同时存在，由配置开关控制是否做自动注入。

### 3.6 检索结果类型统一（可选但推荐）

- 定义 **RetrievalResult**（或复用现有）：`content: str | Message`，`score: float | None`，`source: Literal["stm","ltm","knowledge"]`，`metadata: dict`。  
- LTM/Knowledge 的 `get()` 可返回 `list[RetrievalResult]` 或 `list[Message]`；若为 RetrievalResult，由策略或 Context 转为 Message 再写入 STM 或合并进 assemble 输出。

---

## 4. 组装策略接口（IContextAssemblyStrategy）细化

### 4.1 接口定义（概念级）

```text
Protocol IContextAssemblyStrategy:
  def assemble_messages(
    self,
    context: IContextReadOnlyView,  # 只读：STM/LTM/Knowledge 引用、Budget、当前 query 槽位、最后一条 user 等
    query: str | None,
    options: dict[str, Any],       # max_tokens, phase, include_ltm, include_knowledge, ltm_mode, ...
  ) -> AssemblyResult
```

- **IContextReadOnlyView**：仅暴露 Context 的读操作与必要引用（如 stm.get(...)、ltm.get(...)、knowledge.get(...)、budget、last_user_message()），避免策略修改 Context 内部状态（写 STM 可通过 View 提供的「注入方法」或由 Context 在策略返回后按 AssemblyResult 执行写入）。

### 4.2 AssemblyResult（策略输出）

- **messages**: list[Message] — 已排序、可含 source 标记的最终消息列表。  
- **enrichment_done**: bool — 是否已执行 LTM/Knowledge 注入（若为 True，调用方不必再写 STM）。  
- **metadata**: dict — 如各来源条数、是否触发压缩、token 估算等，供 Hook/Observability 使用。

若采用「模式 A」，enrichment 由策略内部或 Context 在调用策略前完成：先根据 query 写 LTM/Knowledge 进 STM，再让策略的 assemble_messages 只从 STM 取；此时 AssemblyResult.messages 即 STM.get(...) 的结果（含刚注入的 LTM/Knowledge 消息）。

### 4.3 默认策略（DefaultAssemblyStrategy）

- 行为与当前 DARE 完全一致：  
  - 不执行 LTM/Knowledge 检索；  
  - messages = context.stm_get()（或 stm.get() 无参）；  
  - 不做压缩、不做 mark 过滤。  
- 用于兼容现有所有调用方。

### 4.4 RAGAssemblyStrategy（STM + LTM + Knowledge）

- **输入**：context view、query、options（如 include_ltm=True、include_knowledge=True、ltm_limit=5、knowledge_limit=5、max_tokens、prepend_summary 等）。  
- **enrichment 阶段（在返回 messages 之前）**：  
  1. 若 query 为空，从 last user message 取文本。  
  2. 若启用 query_rewrite，调用 LLM 改写 query（可选）。  
  3. 若 static_control 且 include_ltm：调用 ltm.get(query, limit=...)，将结果转为 Message(s)，写入 STM（带 source=ltm、可选 mark=ltm_injected）。  
  4. 若 include_knowledge：调用 knowledge.get(query, limit=..., score_threshold=...)，排序后转为一条（或多条）Message，写入 STM（带 source=knowledge、可选 mark=knowledge_injected）。  
- **取数阶段**：  
  - stm.get(mark=None, exclude_mark=..., prepend_summary=options.get("prepend_summary", True))。  
  - 若需控 token：在策略内对 messages 做截断或再压缩（或依赖已有 compress 在 assemble 前执行）。  
- **输出**：AssemblyResult(messages=..., enrichment_done=True, metadata={...})。

### 4.5 assemble 的触发顺序（与压缩协同）

建议固定顺序：  
1. **Budget 检查**（可选）：若超限可提前失败或告警。  
2. **Compress（若配置触发）**：根据 token 或条数阈值执行 STM 压缩（见下节）；更新 STM 的 compressed_summary 与 marks。  
3. **Enrichment（若策略需要）**：LTM/Knowledge 检索并写入 STM。  
4. **Assemble messages**：策略从 STM（及可选 LTM/Knowledge 已写入的）取消息，返回 AssemblyResult。  
5. **构建 AssembledContext**：messages = AssemblyResult.messages；tools = listing_tools()；sys_prompt = 合并 skill；metadata 含 AssemblyResult.metadata。

这样「Context 与 STM/LTM/Knowledge 的联动」在流程上完全明确，且可测试。

---

## 5. 压缩与 assemble 的协同（对齐 CONTEXT_COMPRESSION_PLAN + AgentScope）

### 5.1 压缩触发时机

- 在 **assemble 之前** 由 Agent 或 Context 判断：  
  - 条件：STM 的 token 估算（或消息条数）> 配置的 trigger_threshold。  
  - 动作：调用 `Context.compress(**options)`（或直接 `stm.compress(...)`），再执行 assemble。  
- 与 CONTEXT_COMPRESSION_PLAN 阶段 0 一致：先「接好触发点」，再扩展策略。

### 5.2 压缩策略参数（options）

- **strategy**：`truncate` | `dedup_then_truncate` | `summary_preview` | `llm_summary`（后续）。  
- **max_messages**：截断时保留最近 N 条。  
- **trigger_threshold_tokens**：超过则触发压缩（若提供 token 计数器）。  
- **keep_recent**：保留最近 N 条不参与压缩（与 AgentScope 一致）；若存在 tool_use/tool_result，需成对保留（见 AgentScope _compress_memory_if_needed 逻辑）。  
- **prepend_summary**：压缩后是否在 STM 内维护一条「摘要」并在 get_memory(prepend_summary=True) 时前置返回。

### 5.3 STM 侧摘要与 marks

- **compressed_summary**：STM 内部字段（如 `_compressed_summary: str`），压缩后由 compress() 写入；get(..., prepend_summary=True) 时作为一条虚拟 Message 放在列表最前。  
- **mark "compressed"**：被折叠为摘要的旧消息打上 mark；get_memory(exclude_mark="compressed") 时可不返回这些原始条，仅通过 prepend_summary 看到摘要。  
- 摘要结构（可选，对齐 AgentScope）：使用结构化 schema（如 task_overview、current_state、important_discoveries、next_steps、context_to_preserve），便于后续 SessionSummary 或审计复用。

### 5.4 与策略的配合

- **DefaultAssemblyStrategy**：不触发压缩，不改 marks。  
- **RAGAssemblyStrategy**：不在策略内执行 compress，但假定「调用方在 assemble 前已按配置执行过 compress」；策略只负责 enrichment + 从 STM 取数。  
- 这样压缩逻辑集中在 Context/STM，策略只消费「已压缩 + 已 enrichment」的 STM。

---

## 6. 配置与 Builder 集成

### 6.1 Context/Assembly 相关配置项（与 AgentScope 对齐）

以下命名与 AgentScope 的 ReActAgent 构造函数及 CompressionConfig 对齐，便于对照实现。

**Assembly / Enrichment**

- **assembly.strategy**：`"default"` | `"rag"` | 或自定义策略类名。  
- **assembly.include_ltm**：bool，是否在 assemble 前做 LTM 检索并注入（对应 AgentScope 提供 long_term_memory 且 static_control）。  
- **assembly.include_knowledge**：bool，是否做 Knowledge 检索并注入（对应 AgentScope 提供 knowledge）。  
- **assembly.ltm_mode** / **long_term_memory_mode**：`"static_control"` | `"agent_control"` | `"both"`（与 AgentScope 同名）。  
- **assembly.enable_rewrite_query** / **enable_rewrite_query**：bool，是否对 user 句做 LLM 改写再检索（与 AgentScope 同名）。  
- **assembly.ltm_limit**：LTM retrieve 条数（AgentScope retrieve 的 limit，默认 5）。  
- **assembly.knowledge_limit**：Knowledge 检索条数（AgentScope retrieve limit，默认 5）。  
- **assembly.knowledge_score_threshold**：float | None，仅返回 score 高于该阈值的文档。  
- **knowledge**：单实例或 list（与 AgentScope 的 `knowledge: KnowledgeBase | list[KnowledgeBase] | None` 对齐）。

**Compression（与 AgentScope CompressionConfig 对齐）**

- **compression_config.enable** / **compression.enable**：bool，是否启用自动压缩。  
- **compression_config.trigger_threshold** / **compression.trigger_threshold**：int，触发压缩的 token 数阈值。  
- **compression_config.keep_recent**：int，保留最近 N 条不压缩（默认 3）；需保证 tool_use/tool_result 成对。  
- **compression_config.compression_prompt**：str，引导 LLM 生成摘要的 prompt。  
- **compression_config.summary_template**：str，摘要展示模板（占位符如 {task_overview}、{current_state} 等）。  
- **compression_config.summary_schema**：结构化 schema 类型（如 SummarySchema：task_overview、current_state、important_discoveries、next_steps、context_to_preserve）。  
- **compression_config.compression_model** / **compression_formatter**：可选，摘要用模型与 formatter。  
- **compression_config.agent_token_counter**：Token 计数器，用于判断是否超 trigger_threshold。  
- **compression.prepend_summary**：bool，get_memory/STM.get 是否在列表前插入摘要（默认 True）。

### 6.2 Builder 职责

- 根据 Config 创建或选择 **IContextAssemblyStrategy** 实例（如 DefaultAssemblyStrategy / RAGAssemblyStrategy）。  
- 将策略注入 Context（如 `context.set_assembly_strategy(strategy)`）或通过 assemble(options) 传入。  
- 若使用「每轮 enrichment」，Builder 需确保 Context 持有 LTM/Knowledge 引用，且策略能通过 IContextReadOnlyView 访问。

### 6.3 Agent 职责（ReAct / Dare）

- **ReAct**：在每轮循环开始，先判断是否执行 compress（按 Budget/阈值），再调用 `context.assemble(query=..., **options)`；assemble 内部或策略会完成 LTM/Knowledge 注入（若配置）并返回 messages。  
- **Dare**：在 milestone 内同理；若使用 STM 快照/回滚，enrichment 写入的 LTM/Knowledge 消息是否参与快照需约定（建议参与，这样回滚时一起回滚）。

---

## 7. 实施阶段与任务拆分（细化）

### 阶段 0：接好 assemble 前压缩触发（与现有计划一致）

- 在 Agent 主循环中约定：**判断 Budget/阈值 → 若超限则 compress() → 再 assemble()**。  
- 不新增策略，不调用 LTM/Knowledge。  
- **交付**：文档化调用顺序；可选在 ReactAgent/DareAgent 中增加一次 compress 调用点（可由配置关闭）。

### 阶段 1：IContextAssemblyStrategy + DefaultAssemblyStrategy

- 定义 **IContextAssemblyStrategy** 与 **AssemblyResult**（及可选 IContextReadOnlyView）。  
- 实现 **DefaultAssemblyStrategy**：仅从 STM 取全量 messages，与当前行为一致。  
- **Context.assemble(options)** 改为：若存在 strategy 则调用 strategy.assemble_messages(context_view, query, options)，用返回的 messages 构建 AssembledContext；否则保持现有逻辑。  
- **交付**：接口与默认实现；单元测试「默认策略输出与当前 assemble 一致」。

### 阶段 2：当前 query 与只读视图

- 为 Context 增加「当前 query」槽位：`set_current_query(str | None)` / `get_current_query()`；或从 Task 读取。  
- 实现 **IContextReadOnlyView**（或简化版）：暴露 stm、ltm、knowledge、budget、last_user_message()、get_current_query()。  
- assemble(options) 支持 **options["query"]** 或从 view 推导 query，并传入策略。  
- **交付**：query 来源约定；View 实现；assemble 传 query 的测试。

### 阶段 3：STM marks 与 get 扩展

- 扩展 **IShortTermMemory.get**：支持 mark、exclude_mark、prepend_summary（若 STM 实现支持）；InMemorySTM 增加 `_compressed_summary` 与 marks 存储（如 list of (Message, list[str] marks)）。  
- 约定 marks：hint、compressed、可选 ltm_injected/knowledge_injected。  
- **交付**：STM.get 新签名与默认实现；compress 写 summary 与 compressed mark 的占位或最小实现。

### 阶段 4：LTM 检索与注入（static_control，与 AgentScope 对齐）

- 在 **RAGAssemblyStrategy**（或独立 Enrichment 模块）中实现：  
  - 若 ltm_mode 含 static_control 且 include_ltm：调用 **ltm.retrieve(msg_or_query, limit=5)**；**与 AgentScope 一致：retrieve 返回 str**，将该 str 包成一条 `<long_term_memory>...</long_term_memory>` 的 Message，带 source=ltm，写入 STM。  
- **ILongTermMemory** 需提供 **retrieve(msg_or_query, limit=5, **kwargs) -> str**（与 AgentScope LongTermMemoryBase.retrieve 对齐）；可选保留 get() 兼容，但 enrichment 走 retrieve。  
- **交付**：RAGAssemblyStrategy 的 LTM 分支；配置项 assembly.include_ltm、assembly.ltm_mode、assembly.ltm_limit；单测「注入后 STM 含 LTM 消息」。

### 阶段 5：Knowledge 检索与注入

- 在策略中实现：若 include_knowledge：调用 knowledge.get(query, limit=..., score_threshold=...)，按 score 排序，包成 `<retrieved_knowledge>...</retrieved_knowledge>` 的 Message 写入 STM，metadata.source=knowledge。  
- 可选 **query_rewrite**：在检索前调用 LLM 改写 query，再传给 knowledge.get。  
- **交付**：RAGAssemblyStrategy 的 Knowledge 分支；配置项 assembly.include_knowledge、assembly.query_rewrite、assembly.knowledge_limit、assembly.knowledge_score_threshold；单测与简单端到端（ReAct + RAG 策略）。

### 阶段 6：压缩与 STM 摘要（对齐 CONTEXT_COMPRESSION_PLAN 阶段 1–2）

- 实现 **compress(strategy="dedup_then_truncate", max_messages=..., keep_recent=...)** 及 **prepend_summary** 在 get 中的行为。  
- 可选 **strategy="summary_preview"**：将较早历史折叠为一条摘要消息（启发式或后续接 LLM），并设置 compressed_summary + marks。  
- **交付**：compress 多策略；STM.get(prepend_summary=True) 返回摘要前置列表；与 assemble 顺序的集成测试。

### 阶段 7：配置与 Builder 集成

- Config 中增加 **assembly.*** 与 **compression.*** 小节；Builder 根据 Config 实例化策略并注入 Context。  
- 文档更新：DARE_FRAMEWORK_DESIGN 中 4.4 context、4.8 memory、4.9 knowledge 补充「检索融合策略、组装策略、压缩协同」；memory_knowledge README 补充「与 Context 的联动流程」。  
- **交付**：Config 字段；Builder 接线；文档与示例（如 05-dare-coding-agent-enhanced 使用 RAG 策略）。

### 阶段 8（可选）：观测与 Hook

- AssembledContext.metadata 或 AssemblyResult.metadata 中记录：各来源条数、是否触发压缩、token 估算、enrichment_done。  
- HookPhase 已有 BEFORE/AFTER_CONTEXT_ASSEMBLE；在 payload 中携带上述 metadata。  
- **交付**：metadata 约定；Hook 文档更新。

---

## 8. 与 AgentScope 方案对齐

本小节将 DARE 方案与 AgentScope 的 Memory / LTM / Knowledge / 压缩 设计逐项对齐，便于实现时直接参照 AgentScope 的接口与流程。

### 8.1 术语与组件对照

| AgentScope | DARE 本计划 | 说明 |
|------------|-------------|------|
| **Memory** / **MemoryBase** | **STM**（IShortTermMemory） | 当前会话消息存储；AgentScope 称 memory，DARE 称 short_term_memory。 |
| **long_term_memory** | **LTM**（ILongTermMemory） | 跨会话持久记忆。 |
| **KnowledgeBase** / **knowledge**（list） | **Knowledge**（IKnowledge），可 list | 知识库/RAG；AgentScope 支持多实例 list[KnowledgeBase]。 |
| **reply(msg)** | **run(task)** 内每轮或 **ReAct 循环** | 单次“用户进 → 模型出”的入口；DARE 用 assemble + generate 组成一轮。 |
| **formatter.format(msgs)** | **Context.assemble() → AssembledContext** | 组装给模型的 prompt；DARE 通过策略产出 messages 再拼 tools/sys_prompt。 |

### 8.2 单轮 reply 流程对齐（与 AgentScope 一致）

以下顺序与 AgentScope `ReActAgent.reply()` 保持一致，DARE 在 ReAct/Dare 模版中按同序实现即可。

1. **写入用户消息**  
   - AgentScope：`await self.memory.add(msg)`。  
   - DARE：`context.stm_add(user_msg)`（或 STM.add）。

2. **Enrichment：LTM 检索并写入 memory**  
   - AgentScope：若 `_static_control`，`await self._retrieve_from_long_term_memory(msg)` → 调 `long_term_memory.retrieve(msg)` 得 **str**，包成 Msg 写入 `memory.add(retrieved_msg)`。  
   - DARE：若 assembly 策略为 RAG 且 ltm_mode 含 static_control，在 assemble 前调 `ltm.retrieve(msg_or_query, limit)`（返回 **str** 或 list[Message]，见下），包成 `<long_term_memory>...</long_term_memory>` 的 Message，写入 STM。

3. **Enrichment：Knowledge 检索并写入 memory**  
   - AgentScope：若 `self.knowledge` 非空，`await self._retrieve_from_knowledge(msg)` → 从 msg 取 query，可选 query rewrite，对每个 `kb in self.knowledge` 调 `await kb.retrieve(query)` 得 list[Document]，按 score 排序，包成 `<retrieved_knowledge>...</retrieved_knowledge>` 的 Msg，写入 `memory.add(retrieved_msg)`。  
   - DARE：若策略 include_knowledge，取 query（或改写），调 knowledge.get(query, limit, score_threshold)，排序后包成同格式 Message，写入 STM；支持多 knowledge 时合并检索结果再排序。

4. **Reasoning-Acting 循环（每轮迭代）**  
   - **4.1 压缩（若配置）**  
     - AgentScope：`await self._compress_memory_if_needed()`（内部用 exclude_mark=COMPRESSED 取待压缩消息，keep_recent 且保证 tool_use/tool_result 成对，超 trigger_threshold 则 LLM 摘要，再 update_messages_mark(COMPRESSED)、update_compressed_summary）。  
     - DARE：在 assemble 前或循环内调用 `context.compress(**options)`，行为对齐（trigger_threshold、keep_recent、结构化摘要、prepend_summary）。  
   - **4.2 Reasoning**  
     - AgentScope：可选先 `memory.add(plan_notebook.get_current_hint(), marks=HINT)`；`prompt = formatter.format([Msg("system", self.sys_prompt, "system"), *await self.memory.get_memory()])`；用后 `memory.delete_by_mark(HINT)`；再 `await self.model(prompt, tools=..., tool_choice=...)`。  
     - DARE：`assembled = context.assemble()`，其中 messages 来自 `stm.get(mark=..., exclude_mark=..., prepend_summary=True)`（等价 get_memory）；再 `model.generate(assembled)`。  
   - **4.3 Acting**  
     - AgentScope：对每个 tool_call 执行 `toolkit.call_tool_function(tool_call)`，结果包成 Msg，`await self.memory.add(tool_res_msg)`。  
     - DARE：ToolGateway.invoke(...)，结果 `context.stm_add(tool_result_msg)`。

5. **本轮结束：LTM 写入（static_control）**  
   - AgentScope：若 `_static_control`，`await self.long_term_memory.record([*await self.memory.get_memory(exclude_mark=COMPRESSED)])`。  
   - DARE：若 ltm_mode 含 static_control，在“单轮结束”或“会话轮次结束”时调 `ltm.record(msgs)`，msgs 来自 STM（可选 exclude_mark=compressed）。

### 8.3 接口签名对齐

**Memory / STM**

| 能力 | AgentScope（MemoryBase） | DARE 对齐约定 |
|------|-------------------------|----------------|
| 写入 | `async add(memories: Msg\|list[Msg]\|None, marks=None, **kwargs)` | STM：`add(msg)` 或 `stm_add(msg)`；若支持 marks 则 `add(msg, marks=...)`。 |
| 按 ID 删 | `async delete(msg_ids: list[str]) -> int` | STM 可选提供 delete(msg_ids)。 |
| 按 mark 删 | `async delete_by_mark(mark: str\|list[str]) -> int` | STM 扩展：delete_by_mark(mark)，用于 hint 用后清理。 |
| 取消息 | `async get_memory(mark=None, exclude_mark=None, prepend_summary=True, **kwargs) -> list[Msg]` | STM.get(mark=..., exclude_mark=..., prepend_summary=...) 返回 list[Message]。 |
| 更新摘要 | `async update_compressed_summary(summary: str)` | STM 内部 _compressed_summary，压缩时更新。 |
| 更新 mark | `async update_messages_mark(new_mark, old_mark=None, msg_ids=None) -> int` | STM 扩展：压缩后对旧消息打 compressed。 |
| 大小/清空 | `async size() -> int`, `async clear()` | STM 已有 clear；可选 size()。 |

**LTM**

| 能力 | AgentScope（LongTermMemoryBase） | DARE 对齐约定 |
|------|---------------------------------|----------------|
| 开发者用：记 | `async record(msgs: list[Msg\|None], **kwargs) -> None` | ltm.record(msgs)，每轮结束 static_control 时调用。 |
| 开发者用：取 | `async retrieve(msg: Msg\|list[Msg]\|None, limit=5, **kwargs) -> str` | **返回 str**（检索结果拼成一段文本），不是 list[Message]；enrichment 时把该 str 包成 Msg 写入 STM。 |
| 工具：记 | `async record_to_memory(thinking: str, content: list[str], **kwargs) -> ToolResponse` | agent_control 时注册为工具；工具内调 LTM 写接口。 |
| 工具：取 | `async retrieve_from_memory(keywords: list[str], limit=5, **kwargs) -> ToolResponse` | agent_control 时注册为工具；返回给模型的 ToolResponse。 |

**Knowledge**

| 能力 | AgentScope（KnowledgeBase） | DARE 对齐约定 |
|------|----------------------------|----------------|
| 检索 | `async retrieve(query, limit=5, score_threshold=None, **kwargs) -> list[Document]` | knowledge.get(query, limit=..., score_threshold=...) 返回 list 或 list[RetrievalResult]；Document 有 score、metadata.content。 |
| 灌库 | `async add_documents(documents: list[Document], **kwargs)` | knowledge.add(...) 或现有 IKnowledge 写接口。 |
| 工具 | `retrieve_knowledge(query, limit=..., score_threshold=...) -> ToolResponse` | 可选；与 DARE 现有 knowledge_get 工具对齐。 |
| 多实例 | `self.knowledge: list[KnowledgeBase]`，遍历 retrieve 后合并排序 | DARE 可支持 list[IKnowledge] 或单实例；多实例时合并结果再按 score 排序。 |

**压缩配置（与 AgentScope CompressionConfig 对齐）**

| 配置项 | AgentScope | DARE 对齐 |
|--------|------------|-----------|
| 是否启用 | `enable: bool` | compression.enable 或 compression_config.enable |
| 触发阈值（token） | `trigger_threshold: int` | compression.trigger_threshold |
| 保留最近条数 | `keep_recent: int = 3` | compression.keep_recent |
| 压缩用 prompt | `compression_prompt: str` | compression.compression_prompt |
| 摘要展示模板 | `summary_template: str`（含 {task_overview} 等占位符） | compression.summary_template |
| 摘要结构化 schema | `summary_schema: Type[BaseModel]`（如 SummarySchema） | compression.summary_schema |
| 压缩用模型 | `compression_model: ChatModelBase \| None` | 可选；与 compression_formatter 成对 |
| Token 计数 | `agent_token_counter: TokenCounterBase` | 用于判断是否超 trigger_threshold |

### 8.4 配置项命名对齐

与 AgentScope 构造函数/配置对齐的命名建议（DARE Config 或 Builder 参数）：

| 用途 | AgentScope 命名 | DARE 建议 |
|------|-----------------|-----------|
| LTM 模式 | `long_term_memory_mode: "agent_control" \| "static_control" \| "both"` | assembly.ltm_mode 或 long_term_memory_mode |
| 是否改写 query | `enable_rewrite_query: bool = True` | assembly.enable_rewrite_query 或 enable_rewrite_query |
| 多知识库 | `knowledge: KnowledgeBase \| list[KnowledgeBase] \| None` | knowledge: IKnowledge \| list[IKnowledge]，多实例时合并检索 |
| 压缩 | `compression_config: CompressionConfig \| None` | compression_config 或 compression.* 字段（enable, trigger_threshold, keep_recent, summary_template, summary_schema 等） |
| 打印 hint | `print_hint_msg: bool = False` | 可选 observability 配置 |

### 8.5 异步约定

- AgentScope：Memory/LTM 的 add、get_memory、retrieve、record、delete_by_mark、update_messages_mark、update_compressed_summary 均为 **async**。  
- DARE 对齐建议：STM 的 add/get/compress、LTM 的 retrieve/record、Knowledge 的 get、以及 **enrichment 与 assemble** 若内部调上述接口，建议统一为 **async**；或对外提供同步 assemble 时在 Agent 层先 await 异步 enrichment 再调同步 assemble（由实现选择）。

### 8.6 对照小结表

| 能力 | AgentScope | DARE 本计划（对齐后） |
|------|------------|------------------------|
| 检索时机 | reply 开始先 LTM 再 RAG，结果写 memory | 同序：assemble 前 enrichment 先 LTM 再 Knowledge，写 STM |
| LTM 模式 | long_term_memory_mode: static_control \| agent_control \| both | assembly.ltm_mode，同左 |
| LTM.retrieve 返回值 | **str**（拼好的文本） | 对齐为 str 或适配为 str，再包成 Msg 写 STM |
| LTM 工具 | record_to_memory(thinking, content), retrieve_from_memory(keywords, limit) | 同签名注册为工具 |
| Query 来源 | 最后 user 消息 get_text_content() | 显式 query 槽位 / Task / 最后 user |
| Query 改写 | enable_rewrite_query，LLM 改写 | assembly.enable_rewrite_query |
| RAG 结果格式 | `<retrieved_knowledge>` Msg 写 memory | 同左，metadata.source=knowledge |
| LTM 结果格式 | `<long_term_memory>` Msg 写 memory | 同左，metadata.source=ltm |
| Memory marks | hint、compressed | hint、compressed、可选 ltm_injected/knowledge_injected |
| get_memory | mark、exclude_mark、prepend_summary | STM.get 同左 |
| 压缩 | CompressionConfig；trigger_threshold、keep_recent、summary_schema、prepend | 同左，在 assemble 前或循环内执行 |
| 上下文组装 | format([sys_prompt, *memory.get_memory()]) | strategy 产出 messages = STM.get(...)，再拼 sys_prompt/tools → AssembledContext |

---

## 9. 风险与约束

- **兼容性**：默认策略必须与当前 assemble 行为一致，且未配置新策略时不应改变任何调用路径；与 dare_framework 现有组件的兼容性见第 10 节。  
- **异步**：若 LTM/Knowledge 检索或 query_rewrite 为异步，需约定 assemble 为 async 或由 Context 在同步 assemble 内触发并等待异步 enrichment（或 enrichment 在 Agent 层 await 后再调用同步 assemble）。  
- **Dare 快照**：STM 快照/回滚需包含 enrichment 写入的消息，避免回滚后状态不一致。  
- **Token 预算**：enrichment 注入的内容会占用上下文窗口，必要时在策略或 compress 中预留 LTM/Knowledge 的 token 配额，避免超窗。

---

## 10. 与 dare_framework 现有组件的兼容性

本方案在设计上**与 dare_framework 现有组件保持兼容**：不破坏现有调用方，仅做**扩展与可选路径**。以下按依赖 Context/STM/LTM/Knowledge 的模块逐项说明。

### 10.1 接口与契约

| 组件 | 现有约定 | 本方案影响 | 兼容性 |
|------|----------|------------|--------|
| **IContext** | `stm_add`, `stm_get() -> list[Message]`, `stm_clear`, `assemble(**options) -> AssembledContext`, `compress(**options)`, `listing_tools`, `budget_*`；`short_term_memory`, `long_term_memory`, `knowledge` 为 IRetrievalContext。 | **assemble**：保留签名；无策略或默认策略时行为与当前一致（仅 `stm_get()` + tools + sys_prompt）。**stm_get**：可扩展为 `stm_get(self, mark=None, exclude_mark=None, prepend_summary=False)`，**默认参数保持当前行为**（无 mark 过滤、不前置摘要）。 | ✅ 兼容：现有调用 `stm_get()`、`assemble()` 的代码无需修改。 |
| **AssembledContext** | `messages`, `sys_prompt`, `tools`, `metadata`。 | 类型与字段不变；仅 messages 来源可由策略从 STM+enrichment 产生。 | ✅ 兼容。 |
| **IRetrievalContext** | `get(query="", **kwargs) -> list[Message]`。 | 不变；LTM/Knowledge 实现仍满足该接口。 | ✅ 兼容。 |

### 10.2 Agent 层（SimpleChatAgent / ReactAgent / DareAgent）

- **使用方式**：仅调用 `context.stm_add()`、`context.assemble()`、`context.budget_*`、`context.set_skill()`；不直接调 LTM/Knowledge。
- **兼容性**：未注入 assembly 策略时，`assemble()` 仍只做 `stm_get()` + tools + sys_prompt，与当前一致。注入 RAG 策略后，仅在“有 LTM/Knowledge 且配置启用”时多出 enrichment，Agent 代码无需改。

### 10.3 Builder

- **使用方式**：已通过 `with_short_term_memory` / `with_long_term_memory` / `with_knowledge` 注入 STM/LTM/Knowledge 到 Context；从 Config 解析 `long_term_memory`、`knowledge` 并调用 `create_long_term_memory` / `create_knowledge`。
- **兼容性**：Builder 仅需**可选**增加“注入 assembly 策略、压缩配置”等；不注入时与现有一致。Context 上已有 `short_term_memory`、`long_term_memory`、`knowledge`，方案只约定“在 assemble 时如何使用它们”。

### 10.4 Compression（compress_context / compress_context_llm_summary）

- **使用方式**：通过 `context.stm_get()` 取全量消息，经截断/去重/摘要后 `context.stm_clear()` 再 `context.stm_add(...)` 写回。
- **兼容性**：**stm_get()** 若扩展为带可选参数，**无参调用**必须与当前语义一致（返回当前全量消息列表），压缩逻辑无需改。若未来 STM 支持 marks，压缩可**可选**使用 `stm_get(exclude_mark="compressed")` 等，为扩展而非破坏。

### 10.5 Plan（IPlanner / IValidator / IRemediator / IPlanAttemptSandbox）

- **使用方式**：Planner/Remediator 使用 `ctx.stm_get()` 读取消息；Sandbox 使用 `ctx.stm_get()` 做快照、`ctx.stm_clear()` + `ctx.stm_add(msg)` 做回滚。
- **兼容性**：**stm_get()** 无参保持“返回当前消息列表”；快照/回滚语义不变。若 enrichment 将 LTM/Knowledge 结果写入 STM，它们会一并被快照与回滚（方案已约定“建议参与”），行为明确。

### 10.6 Memory 域（IShortTermMemory / ILongTermMemory）

- **IShortTermMemory**：当前 `get(query="", **kwargs)`。方案扩展为可选 `mark`、`exclude_mark`、`prepend_summary`；**默认实现（如 InMemorySTM）** 可在未支持 marks 时忽略这些参数，行为与当前 `get()` 一致。
- **ILongTermMemory**：当前 `get(query, **kwargs) -> list[Message]`、`persist(messages)`。方案为与 AgentScope 对齐引入 **retrieve(msg_or_query, limit) -> str**、**record(msgs)**；建议作为**新增方法**，现有 **get/persist** 保留。现有 RawData/Vector LTM 可实现 retrieve/record 为对 get/persist 的薄封装（如 retrieve：get 后拼成 str；record：persist），或由适配器统一提供，**不破坏仅使用 get/persist 的代码**。

### 10.7 Knowledge 域（IKnowledge）

- **使用方式**：`get(query, **kwargs) -> list[Message]`；Builder 将 IKnowledge 注入 Context，并注册 knowledge_get / knowledge_add 工具。
- **兼容性**：方案仅约定“enrichment 时调 knowledge.get(query, limit=..., score_threshold=...)”；IKnowledge 已支持 **kwargs，现有实现可接受 limit/score_threshold**。不改变 IKnowledge 的公开接口。

### 10.8 Skill / Observability

- **Skill**：Context 的 `set_skill`、`current_skill` 及 assemble 内对 sys_prompt 的 skill 合并逻辑不变；方案不涉及。
- **Observability**：AssembledContext.metadata 可**扩展**记录条数、是否压缩等，为增量字段，不破坏现有 Hook/Telemetry 消费者。

### 10.9 实现时需遵守的兼容性原则

1. **默认即当前**：无 assembly 策略或策略为 DefaultAssemblyStrategy 时，`assemble()` 行为与当前 Context.assemble() 完全一致。
2. **扩展用可选参数**：`stm_get`、`assemble` 等新增参数均为可选，且默认值对应“当前行为”。
3. **LTM 双轨**：保留现有 `get`/`persist`；新增 `retrieve`/`record` 与 AgentScope 对齐，由实现或适配器提供，不删除旧接口。
4. **不收紧类型**：IContext、AssembledContext、IRetrievalContext、IKnowledge 的公开类型与字段不做收缩或移除。

---

本计划可直接用于实现排期与任务拆分；具体类名、方法签名以实际代码为准，本文档保持「方案级」描述，便于后续按阶段落地并更新设计文档。
