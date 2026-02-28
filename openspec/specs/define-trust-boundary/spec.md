# define-trust-boundary Specification

## Purpose
TBD - created by archiving change refactor-layered-structure. Update Purpose after archive.
## Requirements
### Requirement: Security Boundary Interface
The framework SHALL define an `ISecurityBoundary` interface that derives trusted inputs, enforces policy decisions, and executes actions within a sandbox boundary.

#### Scenario: Deriving trusted input
- **WHEN** a proposed tool input is supplied by the model
- **THEN** `ISecurityBoundary.verify_trust` returns a `TrustedInput` with derived risk and metadata.

### Requirement: Security Boundary Minimal Contract
The `ISecurityBoundary` interface SHALL expose a minimal contract that includes:
- verifying trusted input (`verify_trust`)
- checking policy decisions (`check_policy`)
- executing actions safely (`execute_safe`)

#### Scenario: Checking policy
- **WHEN** a tool action is evaluated
- **THEN** `check_policy` returns a decision such as ALLOW or APPROVE_REQUIRED.

### Requirement: Security Boundary Positioning
The agent flow SHALL apply `ISecurityBoundary` checks before invoking tool execution or protocol adapters.

#### Scenario: Enforcing ordering
- **WHEN** an agent prepares to invoke a tool
- **THEN** it verifies trust and policy before calling the tool gateway.

### Requirement: Canonical default security boundary implementation
The security domain SHALL provide a default concrete `ISecurityBoundary` implementation for canonical runtime usage.

#### Scenario: Default boundary derives trusted input
- **WHEN** `verify_trust` is called with untrusted params and context
- **THEN** it returns a `TrustedInput` with normalized params and a valid `RiskLevel`

#### Scenario: Default boundary policy is permissive
- **WHEN** `check_policy` is called with any action/resource/context
- **THEN** it returns `PolicyDecision.ALLOW` by default

#### Scenario: Default boundary executes async call safely
- **WHEN** `execute_safe` wraps an async callable
- **THEN** it awaits the callable and returns the underlying result

### Requirement: DefaultSecurityBoundary 必须保持单一 canonical 导出路径
默认安全边界实现 MUST 仅通过 canonical facade `dare_framework.security` 暴露，禁止并行保留 legacy compatibility shim 导出路径。

#### Scenario: 运行时导入使用 canonical facade
- **WHEN** 运行时或测试代码需要默认安全边界
- **THEN** 导入路径为 `from dare_framework.security import DefaultSecurityBoundary`
- **AND** 运行时行为与导入路径无歧义

#### Scenario: 兼容 shim 路径被移除
- **WHEN** 维护者检查 `dare_framework/security/` 包结构
- **THEN** 不存在 `security/impl/default_security_boundary.py` 的兼容导出文件
- **AND** 文档不再宣称该兼容路径为受支持 API
