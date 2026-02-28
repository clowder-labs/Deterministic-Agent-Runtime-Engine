## ADDED Requirements

### Requirement: Architecture 文档必须维护审批语义决策表

`docs/design/Architecture.md` MUST 包含 plan/tool 两入口的审批语义决策表，明确当前行为、目标行为与迁移策略。

#### Scenario: 审批语义差异可被识别

- **WHEN** 评审者阅读 Architecture 的安全与审批章节
- **THEN** 可看到 plan/tool 入口语义差异与统一策略
- **AND** 不需要从代码逆向推断行为

### Requirement: Architecture 文档必须链接可重建性追踪矩阵

`docs/design/Architecture.md` MUST 提供可重建性追踪矩阵入口，使关键架构约束可跳转到实现与测试证据。

#### Scenario: 架构约束能追踪到实现与测试

- **WHEN** 评审者查看某条架构不变量
- **THEN** 可通过文档链接定位到对应代码与测试证据
