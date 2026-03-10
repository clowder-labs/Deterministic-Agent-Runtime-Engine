# DARE 框架支持 A2A 协议设计方案

本文档以 [A2A Protocol 技术文档](https://a2acn.com/) 与规范为基准，说明 DARE 如何支持该协议，使 DARE 构建的 Agent 能作为 A2A 服务被发现与调用，并可选地作为 A2A 客户端与其他智能体协作。

---

## 1. A2A 协议要点（来自 a2acn.com）

A2A 是**智能体间通信与协作**的开放标准（Google 与 50+ 伙伴共建），与 MCP 分工明确：**MCP 用于智能体与工具/资源集成，A2A 用于智能体与智能体协作**。设计时严格区分二者，DARE 内部继续用 MCP 连工具，A2A 只负责「智能体边界」。

### 1.1 核心概念（规范来源）

| 概念 | 含义（据 [核心概念](https://a2acn.com/docs/concepts)） |
|------|--------------------------------------------------------|
| **AgentCard** | 智能体的身份与能力描述卡，JSON 结构，含 name、description、服务端点、支持的协议能力、认证方式、**技能列表（AgentSkill）**。 |
| **Task** | 任务的定义与**完整生命周期**；有 TaskState、支持创建/执行/完成/取消；见 [Task 概念](https://a2acn.com/docs/concepts/task)。 |
| **Artifact** | 任务相关的**数据制品**，智能体产出的结构化结果；可含多 Part（文本、文件等）；见 [Artifact](https://a2acn.com/docs/concepts/artifact)。 |
| **Message** | 智能体间传递**非工件内容**的基本通信单元；含 role（user/agent）、**parts**、可选 metadata；见 [Message](https://a2acn.com/docs/concepts/message)。 |
| **Part** | Message 或 Artifact 的组成部分；类型包括 TextPart、FilePart（inline base64 或 URI）、DataPart 等。 |

### 1.2 智能体发现（规范来源）

协议支持多种发现方式，见 [Agent 发现机制](https://a2acn.com/specification/discovery)：

- **知名 URI（开放发现）**：`GET https://{agent-server-domain}/.well-known/agent.json` 返回 AgentCard。
- **精选注册表**：通过中央目录按技能、标签等查询（企业场景，首版可不做）。
- **直接配置**：通过配置或私有 API 获取 AgentCard，适合静态/内网。

### 1.3 任务与 JSON-RPC

- 传输：**JSON-RPC 2.0** over HTTP；流式用 **SSE**（如 `tasks/sendSubscribe`）。
- 典型方法：`tasks/send`（同步）、`tasks/sendSubscribe`（流式）、`tasks/get`、`tasks/cancel`。
- 任务生命周期：创建 → 执行 → 状态更新 → 完成/取消；支持长时间运行、实时状态与结果同步（[任务生命周期](https://a2acn.com/docs/topics/life-of-a-task/)）。

### 1.4 流式与异步（规范延伸）

- **流式**：通过 SSE 推送任务状态、增量 Artifact（如 `append: true`、`lastChunk`），适合长文档、大文件分块。
- **异步**：Webhook 推送用于超长任务或无法长连的客户端；首版可不实现，预留扩展。

### 1.5 文件在协议中的约定

- **FilePart** 两种形式（[Key Concepts](https://google.github.io/A2A/topics/key-concepts/) 等）：**inline base64** 或 **URI 引用**。
- **Inline**：服务端在 Part 内携带 base64 数据，传输由服务端在响应中完成。
- **URI**：服务端只提供 URL，**由客户端**对该 URI 发起 GET 拉取，即客户端负责实现传输。

---

## 2. DARE 的目标角色

- **A2A Server（必选）**：把 DARE Agent 暴露为符合 A2A 的服务——提供 AgentCard 发现、实现 `tasks/send` / `tasks/sendSubscribe` / `tasks/get` / `tasks/cancel`，将 DARE 的执行结果映射为 Task 状态与 Artifact。
- **A2A Client（必选）**：DARE 作为调用方，通过发现获取 AgentCard、调用远端 `tasks/send` 等，用于多智能体协作。
- **与 MCP 的关系**：完全沿用 [A2A 与 MCP 对比](https://a2acn.com/docs/topics/a2a-and-mcp/) 的结论——用 MCP 连工具，用 A2A 连智能体；DARE 不把 A2A 当作工具协议使用。

---

## 3. 按 A2A 概念的设计映射

### 3.1 AgentCard

- **规范要求**：身份（name、description、provider）、服务端点 URL、协议能力（如 streaming）、认证 schemes、**技能列表 AgentSkill**（id、name、description、inputModes、outputModes、examples）。
- **DARE 实现**：从项目配置（如 `.dare/config.json`）与 **Skill 目录**（现有 `skill` 模块）只读生成 AgentCard；服务端点由运行时 `base_url` 决定。DARE 的每个 `Skill` 映射为 A2A 的 `AgentSkill`，便于发现与筛选。生成逻辑不启动完整 Agent 运行时，保证 `/.well-known/agent.json` 可快速响应。

### 3.2 Task 与任务生命周期

- **规范要求**：Task 有 id、sessionId、status（TaskState）、artifacts、metadata；支持同步返回与流式推送。
- **DARE 实现**：一次用户请求对应一个 A2A Task。DARE 的 `plan.types.Task` 与执行会话对应 A2A 的 task/session；执行结果与产出汇总为 Task 状态 + Artifact 返回。若实现 `tasks/sendSubscribe`，通过 SSE 推送状态与 Artifact（首版可先做「完成后一次性推送」）。

### 3.3 Message 与 Part

- **规范要求**：Message 有 role、parts、可选 metadata；Part 有 TextPart、FilePart（inline 或 uri）、DataPart 等。
- **DARE 实现**：
  - **入参**：A2A 请求中的 message.parts → 转为 DARE 任务描述与附件。当 `create_a2a_app(..., workspace_dir=...)` 传入 workspace_dir 时，inline FilePart 会被解码并落盘到 `workspace_dir/.a2a_attachments/<uuid>/`；provider-safe URI FilePart 不会被服务端主动拉取，而是以 `{uri, filename, mimeType}` 的形式保留在 `task.metadata["a2a_attachments"]`。图片文件会进入 canonical `Message.attachments`，agent 可按需读取元数据中的本地路径或远端 URI。
  - **出参**：DARE 的回复 → TextPart；若 `RunResult.metadata["a2a_output_files"]` 为路径或 `{path, filename?, mimeType?}` 列表，则每个文件以 FilePart inline（base64）加入 Artifact，单文件超过 `max_inline_bytes`（默认 1MB）的跳过。

### 3.4 Artifact

- **规范要求**：任务产出，可多 Part；支持流式（append、lastChunk 等）。
- **DARE 实现**：从单次 run 的结果中收集「可交付产出」（如 write_file 生成的文件、显式声明的结果），封装为 Artifact。小文件用 FilePart inline base64；大文件（超过 max_inline_bytes，默认 1MB）复制到 `workspace_dir/.a2a_artifacts/<task_id>/`，Artifact 中返回 FilePart 的 **uri**，客户端通过 `GET {base_url}/a2a/artifacts/<task_id>/<filename>` 下载。

---

## 4. 发现机制（对齐规范）

- **知名 URI**：在 A2A Server 的 HTTP 服务上提供 `GET /.well-known/agent.json`，返回上述生成的 AgentCard，完全符合 [发现规范](https://a2acn.com/specification/discovery)。
- **直接配置**：调用方已知 base_url 或 AgentCard 地址时，直接使用，无需发现。
- **认证（可选）**：`Config.a2a.auth` 可写入 AgentCard 的 `auth` 段；`create_a2a_app(..., auth_validate=fn)` 可对 POST / 与 GET /a2a/artifacts/ 要求 `Authorization: Bearer <token>` 并校验。Client 使用 `A2AClient(..., bearer_token=...)` 或 `headers={"Authorization": "Bearer ..."}`。
- 精选注册表、Webhook 发现等按规范后续扩展。

---

## 5. 文件传输（严格按协议）

- **服务端产出为文件时**：小文件用 **inline base64** 放入 Artifact 的 FilePart（服务端实现传输）；大文件用 **URI** 时，由 DARE 提供可 GET 的 URL，**客户端**负责按 URI 拉取。
- **客户端传入文件时**：若请求中为 FilePart inline，服务端可解码使用；若为 URI，DARE 不主动发起服务端下载，而是在 URI 方案属于 provider-safe（`http`/`https`/`data`）时直接透传给模型可见附件，其余 URI 退化为文本占位或要求调用方改为 inline。
- 在类型定义中明确区分 FilePart 的 inline 与 uri 两种形态，在 message_adapter 与 artifact 构建处统一处理。

---

## 6. 传输与协议层

- **JSON-RPC 2.0**：所有 A2A 方法以 JSON-RPC over HTTP 实现，错误按 JSON-RPC 约定返回。
- **HTTP**：使用 ASGI（如 Starlette/FastAPI）或 DARE 可挂载的 HTTP 栈，挂载独立路径（如 `/` 或 `/a2a`），与 CLI 等入口隔离。
- **SSE**：`tasks/sendSubscribe` 的响应为 SSE 流，事件类型与 payload 对齐 A2A 流式约定（任务事件、状态更新、工件更新等）。

### 6.1 与 MCP 的 HTTP/传输实现：是否复用

当前 `dare_framework/mcp/transports/` 提供的是**客户端**能力：DARE 作为 MCP **客户端**连接外部 MCP 服务器（stdio 起子进程、HTTP 用 `HTTPTransport` 发 POST、收 JSON 或 SSE）。MCP 侧**没有** HTTP 服务端实现。

| 角色 | 是否需要 | MCP 是否有可复用实现 | 结论 |
|------|----------|----------------------|------|
| **A2A Server** | DARE 对外提供 HTTP 服务（接收 JSON-RPC、返回 AgentCard、处理 tasks/send 等） | 无（MCP 仅有 client） | **不复用**；A2A server 独立实现 HTTP 服务（如 ASGI/Starlette/FastAPI）。 |
| **A2A Client** | 向远端 A2A 服务发 JSON-RPC（tasks/send、tasks/get）并处理 SSE（sendSubscribe） | 有 `HTTPTransport`（POST + JSON/SSE） | **不直接复用** `HTTPTransport` 类：协议语义不同（A2A 的 method/params/会话 与 MCP Streamable HTTP、Mcp-Session-Id 等不一致），共用易耦合。 |

**建议**：

- **Server**：在 `a2a/server/` 内独立实现 HTTP 路由与 JSON-RPC 分发，与 MCP 无共用。
- **Client**：在 `a2a/client/` 内独立实现 A2A 的 HTTP 调用与 SSE 解析；可与 MCP 共用**同一依赖**（如 `httpx`）和类似的「POST + 解析 SSE」思路，但**不共用** `mcp.transports.HTTPTransport`。
- **可选演进**：若后续在 `dare_framework/infra` 或公共层抽象出「通用 JSON-RPC over HTTP 客户端」（只负责发请求、收 JSON/SSE，与具体协议无关），再让 MCP 的 HTTP 传输与 A2A client 共同使用该抽象，避免重复实现而不混用协议。

---

## 7. 模块与目录建议

在 `dare_framework/a2a/` 下实现，与 `mcp/` 平级，通过适配层对接现有 agent/config/skill/context，不替换其核心逻辑。

```
dare_framework/a2a/
├── __init__.py
├── DESIGN.md
├── types.py                  # 与 A2A 规范一致：AgentCard、Message、Part(Text/File/Data)、TaskState、Artifact、JSON-RPC 请求/响应
├── server/
│   ├── __init__.py
│   ├── agent_card.py         # 从 config + skills 生成 AgentCard（含 AgentSkill 列表）
│   ├── handlers.py           # tasks/send, tasks/sendSubscribe, tasks/get, tasks/cancel
│   ├── message_adapter.py    # A2A Message/Part ↔ DARE 上下文/输入与产出
│   └── transport.py         # HTTP 路由 + /.well-known/agent.json + SSE
├── client/                   # 可选
│   ├── __init__.py
│   ├── discovery.py         # 知名 URI / 直接配置 获取 AgentCard
│   └── client.py            # 调用远程 tasks/send、tasks/get
└── _internal/                # 内部实现（按需）
```

- **types**：与 [A2A 规范](https://a2acn.com/specification/core/) 及核心概念文档一致，便于序列化与校验。
- **server**：只读 config/skill、调用现有 agent 执行、将结果映射回 A2A；不改变现有 CLI/内存运行方式。

---

## 8. 与现有 DARE 组件的衔接

- **config**：提供 agent 名称、描述、技能路径等。`Config.a2a` 为可选 dict（`config.json` 中 `"a2a": {"name", "description", "provider", "capabilities", "auth"}`），`build_agent_card(config, base_url)` 会优先用其覆盖默认的 name/description/provider/capabilities/auth。
- **skill**：只读 skill 元数据用于 AgentCard 与 AgentSkill；执行仍由现有 skill + tool 链完成。
- **agent**：A2A server 将「协议入参」转为 canonical `Message`，调用现有执行入口（如 `IAgentOrchestration.execute`），再将「DARE 结果」转为 Task 状态与 Artifact。
- **context**：A2A Message 的 text/file parts 注入为 canonical `Message.text + attachments`；解析后的附件描述列表（inline 为本地 `path`，remote 为原始 `uri`）仍写入 `message.metadata["a2a_attachments"]` 供 agent/tool 按需读取；Artifact 从 run 结果收集。
- **mcp**：不改动；Agent 内部继续用 MCP 调用工具；A2A 仅负责智能体对外的协议与传输。

### 8.1 与执行层的必要约定（A2A 入参/出参）

以下两项**未**在框架其他模块中自动实现，需约定或扩展：

| 约定 | 说明 | 谁负责 |
|------|------|--------|
| **a2a_attachments 的消费** | 用户通过 A2A 上传的 inline 文件会落盘到 `workspace_dir/.a2a_attachments/<uuid>/`，remote URI 文件不会被服务端主动下载。`message.metadata["a2a_attachments"]` 中每项为 `{path|uri, filename, mimeType}`；图片文件同时会进入 canonical `Message.attachments`。 | Agent 或 prompt 若需读取原始 inline 附件文件，可读取 `message.metadata["a2a_attachments"]` 并按 `path` 访问；若是 remote URI，则由业务决定是否显式读取/抓取。模型可见的图片输入优先通过 `Message.attachments` 进入上下文。 |
| **a2a_output_files 的产出** | A2A 将 `RunResult.metadata["a2a_output_files"]` 视为「本次任务产出的文件」并加入 Artifact（inline 或 URI）。 | 执行层在返回 `RunResult` 前，若有需要作为 A2A 产出返回的文件，应写入 `result.metadata["a2a_output_files"]`（路径字符串列表或 `[{path, filename?, mimeType?}]`）。当前框架未自动收集 write_file 等工具的写入路径，可由业务在 run 后根据执行结果组装，或后续在 tool/agent 层增加统一收集逻辑。 |

---

## 9. 实施顺序建议

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | **types**：按 A2A 规范定义 AgentCard、Message、Part（Text/File/Data）、TaskState、Artifact 及 JSON-RPC 入参/出参。 | 已实现 |
| 2 | **AgentCard + 发现**：从 config + skills 生成 AgentCard；HTTP 提供 `/.well-known/agent.json`。 | 已实现 |
| 3 | **Message/Part 适配**：A2A Message/Part 与 DARE 输入/上下文的互转；FilePart inline/uri 明确处理。 | 已实现 |
| 4 | **handlers**：实现 `tasks/send`、`tasks/get`、`tasks/cancel`。 | 已实现 |
| 5 | **Artifact**：从 run 结果组装 Artifact（TextPart + FilePart inline）；大文件/URI 可后续加。 | 已实现 |
| 6 | **SSE**：实现 `tasks/sendSubscribe`，先「完成后一次性 SSE 推送」。 | 已实现 |
| 7 | **client**：discovery + tasks/send、tasks/get、tasks/cancel、send_subscribe。 | 已实现 |

---

## 10. 参考（均以 a2acn.com 为准）

- [A2A 中文站](https://a2acn.com/)：协议介绍、核心概念、任务生命周期、智能体发现。
- [核心概念](https://a2acn.com/docs/concepts)：AgentCard、Task、Artifact、Message、Part。
- [Task](https://a2acn.com/docs/concepts/task)、[Message](https://a2acn.com/docs/concepts/message)、[Artifact](https://a2acn.com/docs/concepts/artifact)、[AgentCard](https://a2acn.com/docs/concepts/agentcard)。
- [智能体发现](https://a2acn.com/docs/topics/agent-discovery/)、[任务生命周期](https://a2acn.com/docs/topics/life-of-a-task/)、[A2A 与 MCP 对比](https://a2acn.com/docs/topics/a2a-and-mcp/)。
- [Agent 发现机制规范](https://a2acn.com/specification/discovery)、[核心协议规范](https://a2acn.com/specification/core/)。

---

*本设计以 A2A 官网与规范为唯一依据，实现时按上述步骤推进，API 与目录可随实现细节微调。*
