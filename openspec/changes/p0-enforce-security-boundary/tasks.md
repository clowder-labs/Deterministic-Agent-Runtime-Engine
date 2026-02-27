## 1. Security Boundary Wiring

- [x] 1.1 为 security domain 增加默认 boundary 实现（no-op + policy）。
- [x] 1.2 在 builder 增加 `with_security_boundary` 注入与 config 解析。
- [x] 1.3 在 `DareAgent` 工具执行前接入 `verify_trust` 预处理。
- [x] 1.4 在 `DareAgent` 工具执行前接入 `check_policy` 判定分支。

## 2. Policy Decision Integration

- [x] 2.1 统一 `ALLOW / APPROVE_REQUIRED / DENY` 到运行时行为映射。
- [x] 2.2 将 `APPROVE_REQUIRED` 分支接入 approval memory 流程。
- [x] 2.3 为 `DENY` 分支定义稳定错误码和用户可读错误信息。
- [x] 2.4 对接 Hook/Telemetry，确保策略决策可观测。

## 3. Audit Event Contract

- [x] 3.1 定义安全门控相关事件类型与 payload 字段约定。
- [x] 3.2 在 trust 校验与 policy 判定处落审计事件。
- [x] 3.3 增加事件字段契约测试，确保兼容 replay/query。

## 4. Tests and Release Gate

- [x] 4.1 新增单元测试覆盖 allow/deny/approve_required 三路径。
- [x] 4.2 新增集成测试验证高风险工具必须经过 policy gate。
- [x] 4.3 增加回归测试验证无 boundary 时不会 silent bypass。
- [x] 4.4 在 CI 增加本 change 的必过测试分组。
