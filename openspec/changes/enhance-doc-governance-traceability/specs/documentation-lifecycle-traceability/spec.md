## ADDED Requirements

### Requirement: 文档目录结构必须维护统一分层
系统 MUST 维护统一文档目录分层，并为设计文档、分析文档、特性聚合文档、标准文档、临时文档、归档文档定义固定放置路径。

#### Scenario: 文档类型有唯一放置位置
- **WHEN** 维护者新增某类治理文档
- **THEN** 可以根据文档类型映射到唯一推荐目录
- **AND** 导航文档中存在与该映射一致的目录说明

### Requirement: 治理变更必须维护单一聚合入口文档
每个文档治理变更 MUST 提供一个可定位的聚合入口文档，集中链接 proposal/design/specs/tasks、相关 `docs/design` 更新、gap 分析与 TODO 清单证据。

#### Scenario: 新治理变更创建后可定位聚合入口
- **WHEN** 维护者创建新的治理类 OpenSpec change
- **THEN** 仓库中存在与 change-id 对应的聚合入口文档
- **AND** 入口文档包含该 change 的 OpenSpec 与文档证据链接

### Requirement: 治理文档必须声明结构化 frontmatter 元数据
纳入治理追踪的文档 MUST 包含 frontmatter，至少声明追踪主键、主题、文档类型与创建时间，且字段命名遵循仓库统一约定。

#### Scenario: 治理文档可被机器检索挂接
- **WHEN** CI 或脚本扫描治理文档目录
- **THEN** 每个被纳入治理范围的文档均可解析 frontmatter
- **AND** 可依据主键字段将文档挂接到对应 change 聚合入口

### Requirement: 活跃治理索引必须维护状态迁移
系统 MUST 维护活跃治理索引，并在治理任务完成时将条目从 active 状态迁移到 archived 状态，避免活跃视图累积历史噪声。

#### Scenario: 治理任务完成后索引状态收敛
- **WHEN** 某治理 change 的 OpenSpec 任务与 TODO 证据均标记完成
- **THEN** 活跃索引不再列出该条目
- **AND** 归档索引中可追溯到该条目的历史记录与证据路径

### Requirement: 治理 checkpoint 必须具备自动校验能力
治理流程中的关键门禁（文档更新、gap/TODO 映射、聚合入口完整性）MUST 有自动校验脚本并接入 CI gate。

#### Scenario: PR 在缺少治理资产时被 gate 阻断
- **WHEN** 变更触达治理范围文件但缺失聚合入口或 frontmatter 关键字段
- **THEN** CI 校验失败并输出可操作修复提示
- **AND** PR 在补齐治理资产前不得通过完整 gate

### Requirement: 治理 SOP 关键阶段必须 skill 化
治理流程中的关键阶段（至少包含 kickoff、completion、verification）MUST 对应到可调用 skill，并维护 checkpoint 到 skill 的稳定映射关系；该映射 MUST 至少包含两个职责分离 skill：`documentation-management` 与 `documentation-workflow`。

#### Scenario: 治理任务可由 skill 驱动执行
- **WHEN** 维护者或 agent 执行治理类变更
- **THEN** 可定位到 `documentation-management` 与 `documentation-workflow` 的 skill 入口与使用说明
- **AND** 能从映射关系中确认该阶段对应的 gate/checkpoint

### Requirement: 协作流程必须声明 OpenSpec 默认与回退模式
治理流程 MUST 明确 OpenSpec 为默认协作模式，并定义无 OpenSpec 场景下的 TODO-driven 回退流程及后续迁移要求。

#### Scenario: OpenSpec 不可用时仍可保持治理闭环
- **WHEN** OpenSpec 工具不可用
- **THEN** 维护者可按 TODO-driven 回退模式继续执行文档治理任务
- **AND** 一旦 OpenSpec 恢复可用，回退资产可迁移并回写到 OpenSpec change
