# Design: Five-Layer Coding Agent Example

## Context

DARE Framework 引入了五层循环架构（Session → Milestone → Plan → Execute → Tool），这是框架的核心设计理念之一。当前缺少一个完整的、可运行的示例来展示这一架构。

**设计文档基础**：
- `/Users/lysander/.gemini/antigravity/brain/9dfbac58-60a5-466d-b8ec-2fb03e0fd899/implementation_plan.md` - 五层循环实现计划
- `/Users/lysander/.gemini/antigravity/brain/9dfbac58-60a5-466d-b8ec-2fb03e0fd899/gap_tracking.md` - 设计差距跟踪
- `/Users/lysander/.gemini/antigravity/brain/9dfbac58-60a5-466d-b8ec-2fb03e0fd899/agent_boundary_analysis.md` - Agent 边界分析

**已知约束**：
- ✅ `FiveLayerAgent` 已实现（`dare_framework/agent/_internal/five_layer.py`）
- 系统提示词设计未开始（P0 优先级）
- `ISecurityBoundary` 和 `IExtensionPoint` 未集成（P0/P1 优先级）

## Goals / Non-Goals

**Goals**:
1. 提供一个清晰、可运行的五层循环示例
2. 展示如何使用 `FiveLayerAgent` 构建实际应用
3. 验证五层循环设计的完整性和可用性
4. 提供确定性模式（用于测试）和真实模型模式（用于演示）
5. 作为后续功能（系统提示词、HITL、安全边界）的集成测试平台

**Non-Goals**:
1. 不实现生产级的 coding agent（仅作为示例）
2. 不覆盖所有可能的工具（选择代表性工具即可）
3. 不优化模型性能（性能优化是后续工作）
4. 不实现完整的错误恢复机制（保持简单）

## Architecture

### Directory Structure

```
examples/five-layer-coding-agent/
├── README.md                    # 使用指南和架构说明
├── __init__.py
├── agent.py                     # Agent 定义和入口
├── deterministic_agent.py       # 确定性模式（无模型调用）
├── openai_agent.py             # OpenAI 真实模型模式
├── config.yaml                  # 配置文件示例
├── tools/                       # 工具实现
│   ├── __init__.py
│   ├── read_file.py            # 读取文件
│   ├── write_file.py           # 写入文件
│   ├── search_code.py          # 代码搜索
│   ├── run_tests.py            # 运行测试
│   └── edit_file.py            # 编辑文件
├── planners/                    # Planner 实现
│   ├── __init__.py
│   ├── deterministic.py        # 确定性 Planner（测试用）
│   └── openai_planner.py       # OpenAI Planner（真实模型）
├── validators/                  # Validator 实现
│   ├── __init__.py
│   └── simple_validator.py     # 简单验证器
├── tests/                       # 测试
│   ├── __init__.py
│   ├── test_deterministic_agent.py
│   └── test_tools.py
└── workspace/                   # 工作目录（用于测试）
    ├── sample.py
    └── sample_test.py
```

### Component Design

#### 1. FiveLayerAgent 使用方式

```python
from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Context
from dare_framework.model import IModelAdapter
from planners.deterministic import DeterministicPlanner
from validators.simple_validator import SimpleValidator
from tools import ReadFileTool, WriteFileTool, SearchCodeTool

# 创建组件
model = ... # IModelAdapter implementation
context = Context(id="coding-session")
planner = DeterministicPlanner(...)
validator = SimpleValidator()

# 创建工具
tools = [
    ReadFileTool(workspace="./workspace"),
    WriteFileTool(workspace="./workspace"),
    SearchCodeTool(workspace="./workspace"),
]

# 组装 Agent
agent = FiveLayerAgent(
    name="coding-agent",
    model=model,
    context=context,
    planner=planner,
    validator=validator,
    tools=tools,  # FiveLayerAgent 接受 IToolProvider
    max_milestone_attempts=3,
    max_plan_attempts=3,
)

# 执行任务
from dare_framework.plan.types import Task
task = Task(task_id="task-1", description="Read README.md and explain the architecture")
result = await agent.run(task)
```

#### 2. Deterministic Planner

用于测试和验证，不依赖真实模型：

```python
class DeterministicPlanner(IPlanner):
    """确定性计划生成器 - 用于测试"""

    def __init__(self, predefined_plan: ProposedPlan):
        self._plan = predefined_plan

    async def plan(self, context: AssembledContext) -> ProposedPlan:
        """返回预定义的计划"""
        return self._plan
```

#### 3. OpenAI Planner

使用真实 OpenAI 模型生成计划：

```python
class OpenAIPlanner(IPlanner):
    """OpenAI 驱动的计划生成器"""

    def __init__(
        self,
        model: IModelAdapter,
        tool_definitions: list[dict],
        plan_tools: list[str] | None = None,
    ):
        self._model = model
        self._tool_defs = tool_definitions
        self._plan_tools = plan_tools or []

    async def plan(self, context: AssembledContext) -> ProposedPlan:
        """调用模型生成计划"""
        prompt = self._build_planning_prompt(context)
        response = await self._model.generate(prompt)
        return self._parse_plan(response)
```

#### 4. Simple Validator

验证计划和里程碑完成状态：

```python
class SimpleValidator(IValidator):
    """简单验证器 - 检查基本约束"""

    async def validate_plan(
        self, plan: ProposedPlan, ctx: dict[str, Any]
    ) -> ValidatedPlan:
        """验证计划的合法性"""
        # 检查工具是否存在
        # 检查参数完整性
        # 检查循环依赖
        ...

    async def verify_milestone(
        self, result: ExecuteResult, ctx: dict[str, Any]
    ) -> VerifyResult:
        """验证里程碑是否完成"""
        # 检查是否有错误
        # 检查预期输出是否产生
        # 收集证据
        ...
```

### Integration Points

#### With dare_framework

| 组件 | 使用方式 |
|------|---------|
| `FiveLayerAgent` | ✅ 直接从 `dare_framework.agent` 导入使用 |
| `IContext` | 使用 `Context` 类创建实例或让 FiveLayerAgent 自动创建 |
| `IModelAdapter` | 实现自定义 ModelAdapter 或 mock |
| `IToolProvider` | 工具列表会被自动包装为 provider |
| `IPlanner` | 实现自定义 Planner（如 DeterministicPlanner） |
| `IValidator` | 实现自定义 Validator（如 SimpleValidator） |

#### With External Dependencies

| 依赖 | 用途 | 可选性 |
|------|------|--------|
| `openai` | OpenAI API 调用 | 可选（仅 openai_agent.py） |
| `pytest` | 运行测试工具 | 必需（仅测试） |
| `pyyaml` | 配置文件解析 | 必需 |

## Decisions

### Decision 1: 分离确定性模式和真实模型模式

**Rationale**:
- 确定性模式用于单元测试和 CI，不需要 API key
- 真实模型模式用于演示和开发验证
- 两种模式使用相同的 `FiveLayerAgent`，只是 Planner 不同

**Implementation**:
- `deterministic_agent.py` - 使用 `DeterministicPlanner`
- `openai_agent.py` - 使用 `OpenAIPlanner`

### Decision 2: 最小化工具集

**Rationale**:
- 避免示例过于复杂
- 选择代表性工具即可展示架构

**Selected Tools**:
- `read_file` - 读操作（READ_ONLY 风险级别）
- `write_file` - 写操作（IDEMPOTENT_WRITE 风险级别）
- `search_code` - 搜索操作（READ_ONLY 风险级别）
- `run_tests` - 执行操作（NON_IDEMPOTENT_EFFECT 风险级别）
- `edit_file` - 编辑操作（IDEMPOTENT_WRITE 风险级别）

### Decision 3: Mock 未实现的组件

**Rationale**:
- `ISecurityBoundary` 和 `IExtensionPoint` 尚未实现
- 示例需要能够独立运行
- 使用 mock 占位，后续替换为真实实现

**Implementation**:
- 如果 `FiveLayerAgent` 需要这些组件，提供 NoOp 实现
- 在 README 中说明哪些组件是 mock

### Decision 4: 提供配置文件支持

**Rationale**:
- 配置文件更易于调整和维护
- 符合生产环境的最佳实践
- 便于用户理解如何配置 Agent

**Format**: YAML（与项目约定一致）

## Risks / Trade-offs

### Risk 1: ~~FiveLayerAgent 未实现~~ ✅ 已解决

**Status**: ✅ `FiveLayerAgent` 已实现并可用（`dare_framework/agent/_internal/five_layer.py`）

**Original Mitigation** (不再需要):
- ~~与 `FiveLayerAgent` 实现并行开发~~
- ~~如果需要，可以先实现示例的 mock 版本~~
- ~~明确在 README 中说明依赖状态~~

### Risk 2: 设计差距导致示例不完整

**Mitigation**:
- 参考 `gap_tracking.md` 中的 P0 项
- 对于未实现的功能，使用 NoOp 或 TODO 注释
- 在 README 中明确说明当前限制

### Risk 3: 真实模型调用成本

**Mitigation**:
- 默认使用确定性模式
- OpenAI 模式需要显式配置
- 使用 `gpt-4o-mini` 降低成本

## Migration Plan

无需迁移（新增功能）。

## Open Questions

1. **~~FiveLayerAgent 接口是否已定稿？~~** ✅ 已解决
   - ✅ FiveLayerAgent 已实现，接口定义清晰
   - 支持三种模式：Full Five-Layer, ReAct, Simple
   - 示例可以直接基于当前接口开发

2. **系统提示词如何集成？**
   - 当前系统提示词设计未开始（P0）
   - 示例是否需要预留系统提示词占位？

3. **如何处理 HITL（Human-in-the-loop）？**
   - `IExecutionControl` 的 HITL 方法是否可用？
   - 示例是否需要展示 HITL 场景？

4. **是否需要提供多个任务示例？**
   - 单一任务（读取文件并解释）vs 多个任务场景
   - 建议至少提供 3 个典型场景

## Implementation Notes

### Phase 1: 基础骨架（确定性模式）

- 创建目录结构
- 实现确定性 Planner 和 Validator
- 实现基础工具集
- 编写单元测试
- 确保能够运行端到端（无真实模型）

### Phase 2: OpenAI 集成

- 实现 OpenAI Planner
- 实现 OpenAI ModelAdapter 集成
- 提供配置文件支持
- 更新 README 添加环境变量说明

### Phase 3: 完善和文档

- 添加更多任务示例
- 完善错误处理
- 编写完整的 README
- 添加集成测试
