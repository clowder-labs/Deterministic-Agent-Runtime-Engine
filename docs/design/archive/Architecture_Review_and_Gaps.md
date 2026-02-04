# 架构评审与差距分析

> 本文档回答以下问题：
> 1. 架构可扩展吗？
> 2. 人类好读吗？好维护吗？
> 3. 协议和边界接口清晰吗？
> 4. 如何验证框架可用？

---

## 一、可扩展性评估

### 1.1 原设计的扩展点

| 扩展点 | 原设计 | 评分 | 问题 |
|-------|-------|------|------|
| 添加工具 | ToolRegistry.register() | ⭐⭐⭐ | 接口清晰，但缺少开发者指南 |
| 添加技能 | 提到 SkillManager | ⭐⭐ | 骨架中没有定义 ISkill 接口 |
| 添加记忆 | ❌ 未考虑 | ⭐ | 完全缺失 |
| 自定义模型 | IModelAdapter | ⭐⭐⭐ | 接口存在，但实现不够清晰 |
| 生命周期扩展 | ❌ 未考虑 | ⭐ | 没有 Hook 机制 |
| 自定义策略 | IPolicyEngine | ⭐⭐⭐ | 接口存在 |
| 自定义存储 | IEventLog | ⭐⭐⭐ | 接口存在 |

### 1.2 新增的扩展接口

我在 `Interface_Layer_Design_v1.md` 中补充了：

```
新增接口：
├── IMemory          → 记忆能力（短期/长期/情景/语义）
├── ISkill           → 技能定义（复合能力）
├── IHook            → 生命周期钩子
├── IAgent           → Agent 完整定义
├── IToolkit         → 工具集合
└── AgentBuilder     → Agent 构建器（简化组装）
```

### 1.3 未来扩展示例

**添加记忆接口后的使用方式：**

```python
# 现在可以这样扩展
agent = (
    AgentBuilder("my-agent")
    .with_tools(...)
    .with_memory(VectorMemory(...))  # 新增！
    .build()
)
```

**添加 LSP 工具的方式：**

```python
# 只需实现 ITool 接口
class LSPTool(ITool):
    @property
    def name(self) -> str:
        return "lsp"

    async def execute(self, input, context) -> dict:
        # 调用 LSP 服务器
        ...

# 注册到 Agent
agent.with_tool(LSPTool())
```

---

## 二、可读性与可维护性

### 2.1 原设计的问题

```
问题：
1. 文档太多（v2.0, v2.1, v2.2, v2.3, v2.4, Skeleton）
   → 开发者不知道从哪里看起

2. 概念嵌套太深
   → Session Loop > Milestone Loop > Tool Loop > Envelope > DonePredicate

3. 缺少"快速上手"路径
   → 想写个简单 Agent 需要读完所有文档吗？

4. 接口定义分散
   → 有的在设计文档，有的在骨架，没有统一的地方
```

### 2.2 改进措施

**1. 创建文档层次结构：**

```
docs/
├── getting-started.md        # 5分钟快速上手（新增）
├── concepts.md               # 核心概念解释（新增）
├── api-reference/            # API 参考（新增）
│   ├── interfaces.md         # 所有接口定义
│   ├── tools.md              # 内置工具
│   └── events.md             # 事件类型
└── design/                   # 设计文档（原有）
    └── ...                   # 详细设计（给架构师看的）
```

**2. 简化概念解释：**

```
核心概念（精简版）：

Agent = 工具 + 技能 + 记忆 + 模型

执行流程：
Task → Plan → Execute → Verify → Done

信任边界：
LLM 输出不可信 → 安全字段从 Registry 派生
```

**3. 统一接口定义：**

所有接口集中在 `Interface_Layer_Design_v1.md`

---

## 三、协议和边界接口

### 3.1 框架 vs Agent 的边界

```
┌────────────────────────────────────────────────────────────────┐
│                    开发者需要做的                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  必须：                                                   │  │
│  │  • 实现至少一个 ITool                                     │  │
│  │  • 选择或实现一个 IModelAdapter                           │  │
│  │                                                          │  │
│  │  可选：                                                   │  │
│  │  • 实现 ISkill（复合能力）                                │  │
│  │  • 实现 IMemory（记忆）                                   │  │
│  │  • 实现 IHook（生命周期扩展）                             │  │
│  │  • 实现 IVerifier（自定义验证）                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    AgentBuilder                           │  │
│  │  agent = AgentBuilder("name")                            │  │
│  │      .with_tools(...)                                    │  │
│  │      .with_model(...)                                    │  │
│  │      .build()                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
├────────────────────────────────────────────────────────────────┤
│                    框架提供的                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • IRuntime（执行引擎）                                   │  │
│  │  • IEventLog（事件日志）                                  │  │
│  │  • IToolRuntime（工具门禁）                               │  │
│  │  • IPolicyEngine（策略引擎）                              │  │
│  │  • IContextAssembler（上下文装配）                        │  │
│  │  • TrustBoundaryValidator（信任边界）                     │  │
│  │  • CoverageValidator（覆盖验证）                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 最小实现路径

```python
# 开发者最少需要做的事：

# 1. 选择一个工具（或用内置的）
from dare_framework.tools import ReadFileTool, WriteFileTool

# 2. 选择一个模型适配器（或用内置的）
from dare_framework.models import ClaudeAdapter

# 3. 组装 Agent
agent = (
    AgentBuilder("my-agent")
    .with_tools(ReadFileTool(), WriteFileTool())
    .with_model(ClaudeAdapter())
    .build()
)

# 4. 运行
result = await agent.run(Task(description="..."))
```

---

## 四、验证策略

### 4.1 为什么需要 Example Agent？

```
问题：如何知道框架设计是对的？

答案：边开发框架，边开发一个使用框架的 Agent

好处：
1. 每个接口都有真实用例验证
2. 开发者有参考实现
3. 设计缺陷能早期暴露
4. 文档和代码保持同步
```

### 4.2 Example Agent 的定位

```
examples/coding-agent/
├── 验证 ITool 接口    → tools/read_file.py
├── 验证 ISkill 接口   → skills/fix_bug.py
├── 验证 Agent 组装    → agent.py
├── 验证完整流程       → tests/test_agent.py
└── 记录设计反馈       → README.md
```

### 4.3 验证清单

| 验证项 | 验证方法 | 状态 |
|-------|---------|------|
| ITool 接口是否足够 | 实现 4 个工具 | ✅ 结构已创建 |
| ISkill 接口是否合理 | 实现 FixBugSkill | ✅ 结构已创建 |
| IMemory 是否需要 | 尝试实现无记忆的 Agent | 待验证 |
| AgentBuilder 是否易用 | 完整组装一个 Agent | 待验证 |
| 框架边界是否清晰 | 开发者反馈 | 待验证 |

### 4.4 开发顺序建议

```
Phase 1: 接口层
├── 定义所有接口（ITool, ISkill, IMemory, ...）
├── 创建 examples/coding-agent 骨架
└── 验证接口设计

Phase 2: 核心实现
├── 实现 IRuntime（六步编排）
├── 实现 IEventLog（本地 append-only）
├── 实现 IToolRuntime（门禁）
└── 同步更新 coding-agent 示例

Phase 3: 完整验证
├── 完成 coding-agent 实现
├── 运行真实任务
├── 收集反馈，迭代设计
└── 编写文档
```

---

## 五、差距总结

### 5.1 必须补的差距

| 差距 | 优先级 | 解决方案 | 状态 |
|-----|-------|---------|------|
| 缺少 IMemory 接口 | P0 | 已在 Interface_Layer_Design_v1.md 定义 | ✅ |
| 缺少 ISkill 接口 | P0 | 已在 Interface_Layer_Design_v1.md 定义 | ✅ |
| 缺少 IHook 接口 | P1 | 已在 Interface_Layer_Design_v1.md 定义 | ✅ |
| 缺少 Example Agent | P0 | 已创建 examples/coding-agent 骨架 | ✅ |
| 缺少快速上手文档 | P1 | 待创建 getting-started.md | 待做 |

### 5.2 可以后做的事

| 事项 | 优先级 | 说明 |
|-----|-------|------|
| 分布式 EventLog | P2 | 先用本地实现 |
| 沙箱执行 | P2 | MVP 可以不做 |
| Token 化 | P2 | MVP 可以不做 |
| 多 Agent 协调 | P2 | 先专注单 Agent |

---

## 六、结论

### 回答你的问题

**1. 架构可扩展吗？**

> 原设计有一定扩展性（接口化），但缺少 Memory、Skill、Hook 等关键扩展点。
> 我已补充完整的接口层设计，现在扩展性更好。

**2. 人类好读吗？好维护吗？**

> 原设计文档太多、太深，不够友好。
> 需要创建分层文档：快速上手 → 概念 → API → 设计。

**3. 协议和边界接口清晰吗？**

> 原设计的边界不够清晰。
> 我已定义清晰的 "框架提供" vs "开发者实现" 边界。

**4. 如何验证框架可用？**

> 双轨开发：框架 + Example Agent 同步开发。
> 已创建 examples/coding-agent 骨架。

---

*文档状态：架构评审完成，可开始实施*
