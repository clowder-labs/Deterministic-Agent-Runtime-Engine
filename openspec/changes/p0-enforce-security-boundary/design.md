## Context

`ISecurityBoundary` 已在 domain 层定义，但当前 `DareAgent` 主循环主要通过 hook 与审批记忆完成局部门控，缺少统一的 trust/policy 入口。现状下高风险调用在部分路径依赖约定而非强制机制，不利于合规场景中的一致执法与审计追踪。

## Goals / Non-Goals

**Goals:**
- 在工具调用前统一执行 trust 推导与 policy 判定。
- 让 `ALLOW / APPROVE_REQUIRED / DENY` 成为运行时一等决策结果。
- 将审批记忆与 policy gate 对齐为单一控制平面语义。
- 为每次门控决策生成稳定审计事件，支持 query/replay。

**Non-Goals:**
- 本次不引入复杂 RBAC/ABAC DSL 引擎。
- 本次不改造所有工具实现内部安全策略，仅收敛调用边界。
- 本次不处理分布式多节点策略一致性。

## Decisions

### Decision 1: 安全边界在 Agent Tool Loop 强制执行
- 在 `DareAgent` 工具调用路径中加入显式 preflight：`verify_trust -> check_policy`。
- preflight 失败或拒绝时，不进入 `ToolGateway.invoke(...)`。
- 理由：把安全检查放在副作用边界之前，避免遗漏与旁路。
- Alternatives:
  - 在 `ToolGateway` 内部做隐式校验：可行，但会弱化 agent 侧可观测上下文。
  - 仅依赖 hooks 拦截：灵活但不具备强制约束。

### Decision 2: policy 决策与审批记忆采用单向衔接
- `APPROVE_REQUIRED` 统一转入现有 approval memory 流程。
- `DENY` 直接失败并记录结构化错误码。
- `ALLOW` 才允许继续调用工具。
- 理由：避免“双重审批系统”导致语义冲突。

### Decision 3: Builder 提供默认 boundary 注入
- 新增 builder 注入点（例如 `with_security_boundary()`），并支持 config 驱动默认实现。
- 开发环境可选 no-op，生产默认 policy boundary。
- 理由：保持向后兼容的同时，推动默认安全基线。

### Decision 4: 审计事件模型统一
- 新增/统一事件类型（示例：`security.trust_verified`、`security.policy_checked`、`security.policy_denied`）。
- 事件 payload 要包含 capability、decision、reason、request_id（若进入审批）。
- 理由：支持运行后追责与复验。

## Risks / Trade-offs

- [Risk] 旧流程依赖“隐式放行”，接入后可能出现行为收紧导致任务失败。  
  → Mitigation: 增加过渡配置与清晰错误提示，先灰度启用严格策略。
- [Risk] 双重门控（policy + approval）可能增加时延。  
  → Mitigation: policy 快速判定并缓存只读策略；仅高风险路径进入审批等待。
- [Risk] 事件字段不统一导致后续审计困难。  
  → Mitigation: 在实现前先冻结事件字段契约并加契约测试。

## Migration Plan

1. 先引入默认 boundary 实现与 builder 注入，不改变现有工具语义。
2. 在 `DareAgent` 工具 preflight 接入 boundary，并加 feature flag 控制。
3. 打通 `APPROVE_REQUIRED` 到 approval memory，统一返回与事件格式。
4. 开启集成回归（allow/deny/approve_required）并在 CI 中设为必过。
5. 切换默认到 strict policy 模式，保留短期回滚开关。

Rollback:
- 将配置切回 no-op boundary 或禁用 strict preflight 分支，恢复原有行为。

## Open Questions

- policy 判定是否需要按 tool namespace 区分不同默认策略？
- `verify_trust` 产物是否需要写入 context 供后续 validator 使用？
- 对于 `APPROVE_REQUIRED` 超时，是否统一落为 `DENY` 还是可重试状态？
