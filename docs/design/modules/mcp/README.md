# Module: mcp

> Status: detailed design aligned to `dare_framework/mcp` (2026-02-25).

## 1. 定位与职责

- 负责 MCP server 配置加载、client 构建与连接生命周期。
- 把远端 MCP tools 转换为本地 `IToolProvider`，纳入统一 ToolManager 调度。

## 2. 依赖与边界

- 核心协议：`IMCPClient` (`dare_framework/mcp/kernel.py`)
- 核心配置：`MCPServerConfig`, `MCPConfigFile`, `TransportType` (`dare_framework/mcp/types.py`)
- 默认组件：
  - `MCPConfigLoader`（目录扫描 + JSON/YAML/Markdown 解析）
  - `MCPClientFactory`（按 transport 构建 client）
  - `MCPToolProvider`（`McpToolManager`）
- 边界约束：
  - MCP 仅负责“远端能力接入”，不负责工具安全策略最终判定。

## 3. 对外接口（Public Contract）

- `IMCPClient.connect() / disconnect()`
- `IMCPClient.list_tools() -> list[ITool]`
- `IMCPClient.call_tool(tool_name, arguments, context) -> ToolResult`
- `load_mcp_configs(paths, workspace_dir, user_dir) -> list[MCPServerConfig]`
- `create_mcp_clients(configs, connect=False, skip_errors=True) -> list[IMCPClient]`
- `MCPToolProvider.list_tools(mcp_name=None) -> list[ITool]`

## 4. 关键字段（Core Fields）

- `MCPServerConfig`
  - `name`, `transport`, `command`, `env`
  - `url`, `headers`
  - `endpoint`, `tls`
  - `timeout_seconds`, `enabled`, `cwd`
- `MCPConfigFile`
  - `source_path`
  - `servers`

## 5. 关键流程（Runtime Flow）

```mermaid
flowchart TD
  A["Scan .dare/mcp/*.json|yaml|md"] --> B["MCPConfigLoader.load"]
  B --> C["MCPServerConfig[]"]
  C --> D["MCPClientFactory.create"]
  D --> E["IMCPClient.connect + list_tools"]
  E --> F["MCPToolProvider cache tools"]
  F --> G["ToolManager.refresh registers capabilities"]
  G --> H["Agent tool loop invoke"]
```

## 6. 与其他模块的交互

- **Tool**：作为 `IToolProvider` 被 ToolManager 接管。
- **Config**：读取 `config.mcp` / `config.mcp_paths`。
- **Agent/Builder**：在构建时注入 MCP provider 到 tool gateway。

## 7. 约束与限制

- grpc transport 在 factory 中仍标记为未实现。
- MCP tool 风险等级/审批字段依赖 server 提供，可信化仍需 policy 层二次校验。

## 8. TODO / 未决问题

- TODO: 接入 `ISecurityBoundary` 做 MCP 工具策略门控。
- TODO: 明确 transport 安全隔离与 sandbox 策略。
- TODO: 增加断线重连与健康检查策略。

## 能力状态（landed / partial / planned）

- `landed`: 见文档头部 Status 所述的当前已落地基线能力。
- `partial`: 当前实现可用但仍有 TODO/限制（见“约束与限制”与“TODO / 未决问题”）。
- `planned`: 当前文档中的未来增强项，以 TODO 条目为准，未纳入当前实现承诺。

## 最小标准补充（2026-02-27）

### 总体架构
- 模块实现主路径：`dare_framework/mcp/`。
- 分层契约遵循 `types.py` / `kernel.py` / `interfaces.py` / `_internal/` 约定；对外语义以本 README 的“对外接口/关键字段/关键流程”章节为准。
- 与全局架构关系：作为 `docs/design/Architecture.md` 中对应 domain 的实现落点，通过 builder 与运行时编排接入。

### 异常与错误处理
- 参数或配置非法时，MUST 显式返回错误（抛出异常或返回失败结果），禁止静默吞错。
- 外部依赖失败（模型/存储/网络/工具）时，优先执行可观测降级策略：记录结构化错误上下文，并在调用边界返回可判定失败。
- 涉及副作用或策略判定的失败路径，MUST 保留审计线索（事件日志或 Hook/Telemetry 记录），以支持回放和排障。

### 测试锚点（Test Anchor）

- `tests/unit/test_mcp_manager.py`（MCP manager 装配与生命周期）
- `tests/unit/test_mcp_client.py`（MCP client 连接与调用基线）
