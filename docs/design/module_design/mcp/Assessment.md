# MCP Domain Assessment

> Status: draft (2026-02-03). Scope: `dare_framework/mcp` only.

## 1. Scope & Responsibilities

- Load MCP server configs from disk.
- Create and manage MCP clients.
- Expose MCP tools as `IToolProvider`.

## 2. Current Public Surface

`dare_framework.mcp` exports:
- Types: `MCPConfigFile`, `MCPServerConfig`, `TransportType`
- Interfaces: `IMCPClient`

Supported defaults live in `dare_framework.mcp.defaults`.

## 3. Findings

1. **Facade was too broad**
   - Client/loader/factory/tool-provider should be defaults, not core API.

2. **Kernel boundary not explicit**
   - `IMCPClient` should live in kernel for stable boundary.

3. **Policy hooks missing**
   - Tool policy and approval rules for MCP tools are not enforced at MCP layer.

## 4. Minimal Public Surface (Proposed)

- **Keep in `dare_framework.mcp`**:
  - `IMCPClient`, config types.
- **Move defaults to `dare_framework.mcp.defaults`**:
  - `MCPClient`, `MCPConfigLoader`, `MCPClientFactory`, `MCPToolProvider`, helpers.

## 5. Doc Updates Needed

- Update module index to include MCP docs.
- Align tool module doc references to `MCPToolProvider` as defaults.

