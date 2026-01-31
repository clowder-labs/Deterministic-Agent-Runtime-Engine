# Module: security

> Status: interface-only (2026-01-31). TODO indicates missing implementation and integration.

## 1. 定位与职责

- 提供 Trust / Policy / Sandbox 的统一边界与接口规范。
- 作为模型不可信输入的“可信化”入口，保证风险字段来自 registry。

## 2. 关键概念与数据结构

- `RiskLevel`：能力风险等级（read_only / idempotent_write / compensatable / non_idempotent_effect）。
- `PolicyDecision`：ALLOW / DENY / APPROVE_REQUIRED。
- `TrustedInput`：从不可信输入派生的可信参数集合。
- `SandboxSpec`：沙箱执行参数（占位）。

## 3. 关键接口

- `ISecurityBoundary.verify_trust(...)`：从 registry 推导可信输入。
- `ISecurityBoundary.check_policy(...)`：策略评估。
- `ISecurityBoundary.execute_safe(...)`：沙箱执行包装。

## 4. 与其他模块的交互

- **Plan**：Validator 可调用 registry 派生风险元数据。
- **Tool**：Tool invocation 应受 policy gate 约束（TODO）。
- **Agent**：执行计划前与工具调用前应调用 policy gate（TODO）。

## 5. 现状与限制

- 当前仅有接口与类型定义，无默认实现。
- DareAgent 未接入 SecurityBoundary（TODO）。

## 6. TODO / 未决问题

- TODO: 提供默认 Policy/Sandbox 实现。
- TODO: 在 Agent 的 Plan→Execute 与 Tool invoke 前接入 policy gate。
- TODO: 与 HITL (`IExecutionControl`) 形成审批闭环。
