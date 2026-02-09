# Module: mcp

> Status: draft (2026-02-03). Aligned to `dare_framework/mcp`.

## 1. 定位与职责

- 负责 MCP (Model Context Protocol) 客户端接入。
- 将 MCP server 的工具封装为 `IToolProvider` 以接入 ToolManager。
- 提供配置加载（`.dare/mcp/*.json`）与 client 工厂。

## 2. 关键概念与数据结构

- `MCPServerConfig` / `MCPConfigFile`：MCP 配置类型。
- `IMCPClient`：MCP 客户端稳定接口（kernel）。
- `MCPToolProvider`：将 MCP tools 暴露为 ITool。

## 3. 当前实现

- `MCPClient`：基于 transport 的 JSON-RPC 客户端。
- `MCPConfigLoader` / `load_mcp_configs`：读取 MCP 配置文件。
- `MCPClientFactory` / `create_mcp_clients`：按配置创建客户端。
- `MCPToolProvider`：将 MCP tools 缓存并转换为 ITool。

## 4. 与其他模块的交互

- **Tool**：`MCPToolProvider` 实现 `IToolProvider`，注册到 ToolManager。
- **Agent/Builder**：当 `config.mcp_paths` 设置时，builder 自动加载 MCP tools。

## 5. 约束与限制

- 目前仅支持 stdio/http/grpc transport 组合的基础配置。
- MCP tools 的风险级别/审批信息依赖 server 侧提供。

## 6. Public Surface

- `dare_framework.mcp`：仅导出 `IMCPClient` + config types。
- `dare_framework.mcp.defaults`：默认实现（client/loader/factory/tool_provider）。

## 7. TODO / 未决问题

- TODO: 增强 MCP tool 的 policy gate（allowlist/approval）。
- TODO: 明确 transport 安全边界与 sandbox 策略。
