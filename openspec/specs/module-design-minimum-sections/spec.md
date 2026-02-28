# module-design-minimum-sections Specification

## Purpose
Ensure every module design document under `docs/design/modules/*/README.md` explicitly satisfies the minimum completeness standard so the system can be reconstructed from documentation.
## Requirements
### Requirement: 模块设计文档必须显式包含最小完备 5 类章节

`docs/design/modules/*/README.md` SHALL 显式包含并可定位以下 5 类内容：总体架构、核心流程、数据结构、关键接口、异常与错误处理。

#### Scenario: 任意模块文档可定位 5 类内容
- **WHEN** 评审者检查任意 `docs/design/modules/<module>/README.md`
- **THEN** 文档可定位到总体架构、核心流程、数据结构、关键接口、异常与错误处理五类内容

### Requirement: 补充章节必须包含实现与测试证据锚点

新增的最小标准补充内容 MUST 给出该模块对应的实现路径/接口路径与测试路径，确保文档可追溯到代码与验证事实。

#### Scenario: 模块补充段落同时包含实现与测试证据路径
- **WHEN** 评审者阅读模块文档补充段落
- **THEN** 可以看到对应 `dare_framework/<domain>/` 路径或接口文件引用
- **AND** 可以定位到至少一个验证该能力的测试文件或测试用例

### Requirement: DG-007 完成后必须回写 TODO 证据

当 DG-007 完成时，`docs/todos/archive/2026-02-27_design_code_gap_todo.md` MUST 将 DG-007 标记为 `done` 并附上文档变更证据与 OpenSpec change 路径。

#### Scenario: DG-007 状态已回写
- **WHEN** 检查 gap TODO 表中 DG-007 行
- **THEN** 状态为 `done`
- **AND** Evidence 字段包含模块文档路径与本 change 路径

### Requirement: 最小章节标准之外必须包含状态校准

模块设计文档除了满足“总体架构/核心流程/数据结构/关键接口/异常处理”五类最小章节外，MUST 对关键能力给出 `landed` / `partial` / `planned` 的当前状态，避免“仅补章节、不校状态”。

#### Scenario: 模块文档可区分已落地与待落地能力

- **WHEN** 评审者查看任意模块 README
- **THEN** 能定位到关键能力状态标记（landed/partial/planned）
- **AND** 不会把已实现能力继续描述为“未实现”

### Requirement: 全量设计评审应周期性执行并回写结果

文档治理 MUST 支持周期性全量评审，并把结果写入 `docs/todos` 的 gap 分析与 TODO 清单，再映射到 OpenSpec change 执行。

#### Scenario: 全量评审流程闭环

- **WHEN** 发起一次全量设计评审
- **THEN** 先更新设计文档，再生成 gap 与 TODO，再推进 OpenSpec 修复
- **AND** 完成后回写 evidence 并归档评审产物

### Requirement: 模块文档必须维护显式测试锚点或缺失声明

每个 `docs/design/modules/*/README.md` MUST 包含“测试锚点（Test Anchor）”段落。
若该模块暂无直接单测，MUST 明确缺失声明并链接对应补测 TODO 项。

#### Scenario: 模块文档可直接定位验证入口
- **WHEN** 评审者阅读任一模块 README
- **THEN** 能定位到至少一个测试文件路径
- **AND** 若无直接单测，文档明确给出缺失说明与补测追踪链接

### Requirement: 过渡性缺失声明关闭后必须回写直连测试锚点

当模块从“缺失声明”进入“测试资产已补齐”状态时，模块 README MUST 用直连测试路径替换过渡声明，并在 TODO 台账中关闭对应事项。

#### Scenario: 模块从过渡态切换到闭环态
- **WHEN** 维护者补齐模块直连单测
- **THEN** 模块文档测试锚点使用直连测试路径
- **AND** 对应 full-review TODO 项状态更新为 done
