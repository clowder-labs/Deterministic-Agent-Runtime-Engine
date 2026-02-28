## ADDED Requirements

### Requirement: 过渡性缺失声明关闭后必须回写直连测试锚点

当模块从“缺失声明”进入“测试资产已补齐”状态时，模块 README MUST 用直连测试路径替换过渡声明，并在 TODO 台账中关闭对应事项。

#### Scenario: 模块从过渡态切换到闭环态
- **WHEN** 维护者补齐模块直连单测
- **THEN** 模块文档测试锚点使用直连测试路径
- **AND** 对应 full-review TODO 项状态更新为 done
