## Why

当前框架把 `LLM 不可信` 作为核心不变量，但安全边界仍主要停留在接口层，关键门控尚未强制接入主执行路径。结果是策略决策、审批链路与工具调用之间存在绕过风险，难以满足“默认安全、可审计、可复验”的 P0 目标。

## What Changes

- 在运行时引入默认安全边界实现（no-op 仅用于开发，policy 作为生产默认候选），并由 builder 统一注入。
- 在工具调用前强制执行 `verify_trust` 与 `check_policy`，禁止未校验调用直接进入 `ToolGateway.invoke(...)`。
- 打通 policy 决策与审批记忆：`ALLOW` 直接执行，`APPROVE_REQUIRED` 进入审批流，`DENY` 结构化拒绝并记录审计事件。
- 统一策略事件与错误码，确保 Hook/Telemetry/EventLog 能还原一次完整门控决策链。
- 增加面向 P0 的单元/集成回归，覆盖允许、拒绝、待审批三类路径。

## Capabilities

### New Capabilities
- `security-policy-gate`: 在 agent 执行路径中提供统一 trust + policy 门控能力，并输出可审计决策记录。

### Modified Capabilities
- `define-trust-boundary`: 将 trust 推导从“设计约束”升级为“执行时强制步骤”。
- `core-runtime`: 将工具调用前的 policy gate 纳入主循环，补齐拒绝与审批的标准行为。
- `validation`: 增加针对安全门控决策的可验证断言与回归门禁。

## Impact

- Affected code:
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/builder.py`
  - `dare_framework/security/kernel.py`
  - `dare_framework/security/types.py`
  - `dare_framework/config/types.py`
  - `tests/unit/test_five_layer_agent.py`
  - `tests/unit/test_tool_gateway.py`
  - `tests/integration/test_example_agent_flow.py`
- Affected runtime behavior:
  - 高风险工具调用默认进入策略门控。
  - 审批记忆与策略决策语义统一。
- Dependency/API impact:
  - 新增可选安全边界注入配置，默认行为更严格（可能暴露既有“隐式放行”路径）。
