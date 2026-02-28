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

### Requirement: 可重建性治理必须维护文档生命周期依赖链
可重建性治理 MUST 明确并执行 `standards -> feature aggregation -> design -> gap analysis -> TODO -> execution evidence -> archive` 的生命周期依赖关系。

#### Scenario: 治理任务可按依赖链追溯
- **WHEN** 评审者抽查任一治理 change
- **THEN** 能从聚合入口按依赖链定位到对应文档资产
- **AND** 依赖链中每个阶段都有状态与证据锚点

### Requirement: 可重建性治理门禁必须提供自动化检查
可重建性治理流程 MUST 将以下门禁纳入自动化检查：文档先行更新、gap 分析存在性、TODO 到 OpenSpec task 的映射完整性。

#### Scenario: 缺失治理门禁资产时自动阻断
- **WHEN** 提交包含治理相关实现或文档变更但未补齐 gap/TODO 映射
- **THEN** 自动化检查报告失败
- **AND** 报告指出缺失项与期望文件路径

### Requirement: 可重建性治理必须维护 checkpoint-skill 映射
可重建性治理 MUST 维护一份 checkpoint 到 skill 的映射清单，确保 SOP 的关键阶段具备可执行承载并可被审计。

#### Scenario: 评审者可验证 SOP skill 化覆盖
- **WHEN** 评审者检查治理流程资产
- **THEN** 能定位到关键 checkpoint 对应的 skill 名称与路径
- **AND** 能确认该映射与 CI 检查项一致

### Requirement: 特性聚合文档必须作为状态单一真相源
治理 change 的生命周期状态 MUST 以 `docs/features/<change-id>.md` 聚合文档为单一真相源，其他关联文档不得维护与其冲突的主状态。

#### Scenario: 状态一致性可自动校验
- **WHEN** CI 或评审检查同一 change 的多份文档状态
- **THEN** 聚合文档状态与关联文档不会出现冲突主状态
- **AND** 若存在冲突，检查会报告并阻断合入
