## Why

当前设计文档已基本对齐实现，但距离“仅依赖文档即可重建系统”仍有关键缺口：缺少统一追踪矩阵、审批语义决策表与重建 SOP。若不补齐，这些隐性约束会在后续迭代中再次漂移，导致文档逐步失真。

## What Changes

- 新增“文档可重建性治理”能力：建立 Doc->Code->Test 追踪矩阵与重建执行基线。
- 在架构文档治理中增加“语义决策表”要求，明确 plan/tool 审批语义与迁移路径。
- 在模块文档治理中增加“实现锚点 + 状态标签”硬约束，减少 as-is/to-be 混淆。
- 基于 gap 分析产出 P0/P1 TODO，并绑定 OpenSpec 执行。

## Capabilities

### New Capabilities

- `design-reconstructability-governance`: 定义文档可重建性的追踪矩阵、重建 SOP 和持续校验要求。

### Modified Capabilities

- `architecture-documentation-alignment`: 增加架构级语义决策与追踪矩阵入口要求。
- `module-design-minimum-sections`: 增加模块级实现锚点与能力状态标签要求。

## Impact

- 主要影响文档治理资产：
  - `docs/design/Architecture.md`
  - `docs/design/modules/*/README.md`
  - `docs/guides/Documentation_First_Development_SOP.md`
  - `docs/todos/*`
- OpenSpec 影响：
  - 新增 `design-reconstructability-governance` 主 specs
  - 修改现有 `architecture-documentation-alignment` 与 `module-design-minimum-sections` specs
