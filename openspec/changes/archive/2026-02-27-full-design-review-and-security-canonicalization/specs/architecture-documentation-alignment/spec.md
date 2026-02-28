## ADDED Requirements

### Requirement: Architecture 与模块设计文档必须执行完整评审

`docs/design` 的治理流程 MUST 支持“完整评审”模式：一次评审中至少覆盖 `Architecture.md` 与全部 `docs/design/modules/*/README.md`，并识别与当前实现冲突的断言。

#### Scenario: 完整评审覆盖范围可核验

- **WHEN** 维护者执行一次设计文档评审
- **THEN** 评审结果包含 Architecture 与全部模块 README 的检查结论
- **AND** 结论至少区分 `aligned` / `drift` 两类状态

### Requirement: Architecture 文档不得保留已失效的核心运行态断言

`docs/design/Architecture.md` MUST 与当前核心运行态一致，不得继续宣称以下已落地能力“未实现”：step-driven execute loop、plan/tool security gate、plan attempt sandbox baseline。

#### Scenario: 核心运行态断言与代码一致

- **WHEN** 评审者阅读 Architecture 的“现实差距 / 核心流程”章节
- **THEN** 不存在“ValidatedPlan.steps 未驱动执行”或“security gate 未接入”等失效断言
- **AND** 文档仅保留仍未闭环的能力作为 TODO

### Requirement: 完整评审结果必须沉淀为 gap 分析与 TODO 清单

每次完整评审 MUST 在 `docs/todos/` 生成对应的 gap 分析文档与 TODO 清单，并给出可追溯证据链接。

#### Scenario: 评审产物具备可追溯性

- **WHEN** 维护者检查该轮评审产物
- **THEN** 可定位到 gap 文档、TODO 文档和对应实现/文档证据
