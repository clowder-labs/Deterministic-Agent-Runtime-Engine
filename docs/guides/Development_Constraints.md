# DARE 开发约束（面向 AI/Human 开发者）

适用对象：在本仓库编写代码的所有开发者（含 Codex、Claude 等 AI Agent）。目标：在不破坏架构的前提下，产出简洁、可验证、可维护的代码。

## 总则
- 先看架构：不得破坏五层循环编排骨架、系统调用边界与核心接口契约（见 `docs/design/Architecture.md`、`docs/design/Interfaces.md`、`openspec/project.md`；历史参考见 `docs/design/archive/`）。重大能力/接口变更走 OpenSpec。
- 文档一致性：任何代码修改或方案修改，必须同步更新 `docs/design/DARE_Formal_Design.md` 的最终设计与其关联的模块详细设计（`docs/design/modules/`），同时更新 README 并补充对应 example；保证一次修改将所有涉及资料一并校准。
- 状态外化：所有进度、决策、证据写入文件/EventLog，避免依赖模型“记忆”。
- 最小必要变更：新增功能时优先扩展现有组件/接口，避免跨层耦合或绕过 `IToolGateway`/`ISecurityBoundary`。

## 文档先行硬门禁（新增，强制）
- Agent 开发必须先遵循 `docs/guides/` 约束，最低要求：`Development_Constraints.md` + `Documentation_First_Development_SOP.md`。
- 文档管理方式必须遵循 `docs/governance/Documentation_Management_Model.md`（目录分层、文档类型放置、生命周期迁移）。
- 所有代码开发以 `docs/design/` 全量最新设计为准；若实现与文档冲突，必须先更新文档再改代码。
- 设计文档必须可独立重建实现：至少显式描述总体架构、核心流程、数据结构、关键接口、异常错误处理（详见 `docs/design/Design_Doc_Minimum_Standard.md`）。
- 任何 Bug/新增 Feature/重构，必须先执行“文档更新 + gap 分析 + TODO 拆解”，再按 OpenSpec 流程逐项落地。
- 默认采用 OpenSpec 协作；仅在 OpenSpec 不可用时允许 TODO-driven 回退模式，并必须在 OpenSpec 恢复后完成迁移回写。
- 任何治理类文档任务必须使用双技能流程（`.codex/skills/documentation-management/SKILL.md` + `.codex/skills/documentation-workflow/SKILL.md`）或等价自动化流程；旧入口 `.codex/skills/documentation-lifecycle-governance/SKILL.md` 仅用于兼容转发。
- 禁止“先写代码后补文档”；除紧急止血修复外，文档缺失视为任务未开始。紧急修复需在 24 小时内补齐文档与 gap 分析。

## 设计准则（高内聚、低耦合）
- 模块边界：`core` 定义不可变 Kernel contract 与控制面（Layer 0，并在各 domain package 内提供最小默认实现），`components` 提供可插拔组件实现（Layer 2，含 entrypoints 机制），`protocols` 提供协议适配（Layer 1），`builder` 提供组装 API（Layer 3），业务/示例放在 `examples/`；避免跨层耦合与“绕过内核边界”的捷径。
- 接口优先：先定义/复用抽象接口，后实现；遵循 SOLID/DRY/KISS，小函数、小对象，避免静态全局单例。默认使用 `ABC` 定义框架接口；仅在确需结构化子类型匹配时使用 `Protocol`（当前优先用于 Model 相关抽象）。
- 依赖注入：通过构造器或显式参数传递依赖，不隐式从全局获取，以便测试和替换。
- 数据约束：使用 Pydantic 或严格类型别名表达输入输出，不信任 LLM 生成的字段；所有函数/方法必须完整类型标注。Domain 层禁止通过字符串解析推断行为，必须使用强类型（枚举/数据对象）表达语义。
- 兼容策略：当前仓库处于开发阶段，不为历史行为保留保护性兼容分支或回退逻辑；发现设计问题优先重构到清晰职责边界。
- Python 版本策略：最低兼容版本为 Python `3.12`，不再为 Python `3.11` 及更老版本添加兼容代码。

## 测试硬性要求
- 功能即测试：业务逻辑、接口、Bug 修复都必须有对应测试；缺测试的变更视为不完成。
- 覆盖层次：单元测试覆盖核心分支；跨组件交互用 integration；完整编排用 e2e；异步路径用 `pytest-asyncio`。
- 判定标准：确保可信源与不可信源的分支均有断言；对错误分支写回归测试；避免对外部网络/时钟的非隔离依赖（用 fixture/mocks）。
- 工具链：在提交前跑 `ruff`, `black --check`, `mypy --strict`, `pytest`；新增公共接口时同步补充类型/文档示例。

## 可验证性与日志
- 结构化日志：使用 `structlog`，输出包含 `trace_id/task_id/run_id`；开发态用 `debug` 捕获决策路径，稳定态用 `info`，异常用 `warning/error`，避免 `print`。
- 详略得当：调试细节仅在 debug 级别；info 级别聚焦里程碑、状态迁移、风险决策；严禁记录敏感明文（令牌化/脱敏）。
- 证据闭环：所有外部动作都要在 EventLog 落证（工具调用、审批、补救、失败原因），与架构的五个可验证闭环保持一致。

## 代码风格与命名
- 风格：Black（100 列）、Ruff、Google 风格 docstring；保持纯 ASCII 代码与缩进，必要的中文注释简洁清晰。
- 命名：类型/类用 PascalCase，函数/变量用 snake_case，常量 UPPER_SNAKE；命名表达业务意图，不用缩写；文件/模块命名与职责对齐。
- 注释：只为意图、约束或非显然逻辑写注释；接口/公共函数必须有 docstring 说明输入、输出、错误与副作用。

## 复用与依赖
- 先复用后新增：优先使用现有组件（日志、策略、验证器、工具注册表、MCP 客户端），避免重复实现；抽公共逻辑到局部工具函数，不制造过度抽象。
- 依赖管理：慎增依赖，避免引入与现有栈冲突的库；新增依赖需说明必要性和安全性，并补充最小化封装以便替换。

## 安全与信任边界
- 不绕过 `IToolGateway`；高风险能力必须显式审批（HITL/Policy），遵循风险级别与超时约束；EventLog 只追加，不修改/删除。
- 输入消毒：用户/LLM/外部输入一律视为不可信，使用校验器/类型转换；安全关键字段从可信源派生（注册表、策略引擎、配置）。
- 资源控制：异步调用设置超时；任何执行型操作使用沙箱/隔离接口，不直接调用系统命令。

## 交付检查清单
- 架构契约未破坏，信任边界与风险级别保持正确。
- 新增/修改能力对应的测试齐全且可重复。
- 代码通过 `ruff`/`black`/`mypy`/`pytest`，接口/公共函数有 docstring，命名清晰。
- 日志/审计点到位，敏感数据已脱敏，EventLog 记录关键操作。
- 代码改动前已完成设计文档更新；存在对应 gap 分析文档与 TODO 清单，并与 OpenSpec 任务一一对应。
