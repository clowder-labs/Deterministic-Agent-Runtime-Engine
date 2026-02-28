## ADDED Requirements

### Requirement: 模块设计文档必须显式包含最小完备 5 类章节
`docs/design/modules/*/README.md` SHALL 显式包含并可定位以下 5 类内容：总体架构、核心流程、数据结构、关键接口、异常与错误处理。

#### Scenario: 任意模块文档可定位 5 类内容
- **WHEN** 评审者检查任意 `docs/design/modules/<module>/README.md`
- **THEN** 文档可定位到总体架构、核心流程、数据结构、关键接口、异常与错误处理五类内容

### Requirement: 补充章节必须包含实现证据锚点
新增的最小标准补充内容 MUST 给出该模块对应的实现路径或接口路径，确保文档可追溯到代码事实。

#### Scenario: 总体架构与异常处理段落有证据路径
- **WHEN** 评审者阅读模块文档补充段落
- **THEN** 可以看到对应 `dare_framework/<domain>/` 路径或接口文件引用

### Requirement: DG-007 完成后必须回写 TODO 证据
当 DG-007 完成时，`docs/todos/archive/2026-02-27_design_code_gap_todo.md` MUST 将 DG-007 标记为 `done` 并附上文档变更证据与 OpenSpec change 路径。

#### Scenario: DG-007 状态已回写
- **WHEN** 检查 gap TODO 表中 DG-007 行
- **THEN** 状态为 `done`
- **AND** Evidence 字段包含模块文档路径与本 change 路径
