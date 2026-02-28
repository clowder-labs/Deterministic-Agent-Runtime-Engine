## ADDED Requirements

### Requirement: 文档可重建性必须维护统一追踪矩阵

系统 MUST 维护一份可检索的追踪矩阵，覆盖关键能力的 `design requirement -> code anchor -> test evidence -> status` 映射。

#### Scenario: 追踪矩阵可定位关键能力责任

- **WHEN** 维护者检查某条关键设计约束
- **THEN** 能定位到对应实现文件与验证测试
- **AND** 能看到当前状态（implemented/partial/planned）

### Requirement: 文档可重建性必须定义重建 SOP

系统 MUST 提供“按文档重建”SOP，包含最小重建顺序、验收测试集、失败回滚与证据归档规则。

#### Scenario: 重建流程具有标准执行模板

- **WHEN** 新成员仅基于 docs 执行重建
- **THEN** 可按固定步骤完成核心能力重建与验证
- **AND** 过程中的偏差会被记录到 gap/TODO 资产

### Requirement: 可重建性治理必须维护 P0/P1 优先级清单

可重建性治理 MUST 维护 P0/P1 缺口列表，并与 OpenSpec tasks 映射，避免缺口长期悬挂。

#### Scenario: 缺口治理优先级可追踪

- **WHEN** 评审者检查可重建性治理文档
- **THEN** 能看到 P0/P1 列表与对应 OpenSpec change/task 映射
