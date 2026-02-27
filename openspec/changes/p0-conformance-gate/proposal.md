## Why

P0 三项核心能力（安全门控、step 驱动执行、默认事件链）即使实现完成，如果没有统一的门禁规则，后续迭代仍可能回归。需要把“架构不变量”固化为 CI 可执行约束，避免只靠人工评审维护质量。

## What Changes

- 新增 `p0-gate` 测试分组，覆盖安全决策、执行闭环、审计链完整性三大不变量。
- 引入跨模块集成用例，验证 `plan -> execute -> verify` 与 `policy -> approval -> invoke` 的链路一致性。
- 在 CI 中将 `p0-gate` 设为必过检查，未通过禁止合并。
- 定义 P0 指标基线（通过率、关键路径失败率、事件链完整率），作为发布阈值。
- 输出失败诊断模板，帮助快速定位是策略、执行还是审计链回归。

## Capabilities

### New Capabilities
- `p0-conformance-gate`: 将 P0 架构不变量转为自动化测试门禁与发布准入规则。

### Modified Capabilities
- `validation`: 扩展到运行时跨域一致性验证，而不仅是局部单元行为。
- `core-runtime`: 增加面向发布的合规回归门槛定义与校验入口。

## Impact

- Affected code:
  - `tests/unit/*`（新增/重组 P0 关键断言）
  - `tests/integration/*`（新增端到端闭环用例）
  - CI workflow 配置（新增 `p0-gate` job）
  - `docs/` 中开发与发布流程说明
- Process impact:
  - 合并流程新增硬门禁，短期可能降低合并速度但提升稳定性。
  - 需要团队维护 P0 用例与指标基线。
