## MODIFIED Requirements

### Requirement: 文档可重建性必须维护统一追踪矩阵
系统 MUST 维护一份可检索的追踪矩阵，覆盖关键能力的 `design requirement -> code anchor -> test evidence -> status` 映射；对于治理类变更，矩阵还 MUST 显式关联对应 change 的聚合入口文档与 gap/TODO 证据路径。

#### Scenario: 追踪矩阵可定位关键能力责任

- **WHEN** 维护者检查某条关键设计约束
- **THEN** 能定位到对应实现文件与验证测试
- **AND** 能看到当前状态（implemented/partial/planned）
- **AND** 能跳转到关联治理 change 的聚合入口与证据文档

### Requirement: 可重建性治理必须维护 P0/P1 优先级清单
可重建性治理 MUST 维护 P0/P1 缺口列表，并与 OpenSpec tasks 映射；该映射 MUST 具备机器可校验标识（稳定 ID 或 frontmatter 锚点），避免缺口长期悬挂或证据失联。

#### Scenario: 缺口治理优先级可追踪

- **WHEN** 评审者检查可重建性治理文档
- **THEN** 能看到 P0/P1 列表与对应 OpenSpec change/task 映射
- **AND** 能通过稳定标识验证该映射未失效

## ADDED Requirements

### Requirement: 可重建性治理门禁必须提供自动化检查
可重建性治理流程 MUST 将以下门禁纳入自动化检查：文档先行更新、gap 分析存在性、TODO 到 OpenSpec task 的映射完整性。

#### Scenario: 缺失治理门禁资产时自动阻断
- **WHEN** 提交包含治理相关实现或文档变更但未补齐 gap/TODO 映射
- **THEN** 自动化检查报告失败
- **AND** 报告指出缺失项与期望文件路径
