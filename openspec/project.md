# Project Context

## Purpose

**DARE Framework** (Deterministic Agent Runtime Engine) 是一个工业级 AI Agent 执行框架，专为需要高安全性、可审计性和多 Agent 协作的场景设计。

### 核心目标

1. **银行/金融场景** - 强审计、合规、人在回路（Human-in-the-loop）
2. **代码生成场景** - 容错、迭代、外部验证
3. **多 Agent 协作** - 任务租约、冲突处理、统一状态

### 设计理念

| 理念 | 含义 |
|-----|-----|
| **状态外化** | 所有状态存 EventLog/DB，不依赖模型记忆 |
| **LLM 不可信** | Plan 产出只是"意图"，安全关键字段从可信源派生 |
| **外部可验证** | "完成"由外部验证器判定，不信任模型说"done" |
| **增量执行** | 每步做完提交，留清晰交接物 |
| **可审计** | 每个决策有结构化记录 + 证据链 |

## Tech Stack

- **Primary Language**: Python 3.12+
- **Type Checking**: mypy (strict mode)
- **Testing**: pytest + pytest-asyncio
- **Async Runtime**: asyncio
- **Data Validation**: Pydantic v2
- **Configuration**: YAML + pydantic-settings
- **Logging**: structlog (structured logging)
- **Container Runtime**: Docker (for sandbox execution)

### Local Environment

- **python (pyenv)**: 3.12.12 (project default, use for venv/test)
- **python3 (system)**: 3.14.0 (installed via Homebrew; avoid for this repo)

### Optional/Future
- **Event Storage**: PostgreSQL / S3 (for WORM storage)
- **Message Queue**: Redis Streams / Kafka (for distributed mode)
- **Observability**: OpenTelemetry

## Project Conventions

### Code Style

- **Formatter**: Black (line-length: 100)
- **Linter**: Ruff
- **Import Sorting**: isort (compatible with Black)
- **Docstrings**: Google style

```python
# Naming conventions
class ToolRegistry:        # Classes: PascalCase
    _tools: dict           # Private: _prefix

def validate_step():       # Functions: snake_case
    pass

TRUSTED_SOURCES = [...]    # Constants: UPPER_SNAKE_CASE
```

### Type Hints

所有函数必须有完整的类型注解：

```python
async def invoke(
    self,
    tool_name: str,
    input: dict[str, Any],
    context: ExecutionContext,
) -> ToolResult:
    ...
```

### Architecture Patterns

#### 五层循环架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Session Loop (跨 Context Window)                                │
│  └─ Milestone Loop (Observe → Plan → Approve → Execute → Verify) │
│     ├─ Plan Loop (生成有效计划，失败不外泄)                        │
│     ├─ Execute Loop (LLM 驱动执行)                               │
│     └─ Tool Loop (WorkUnit 内部闭环)                              │
└─────────────────────────────────────────────────────────────────┘
```

**Session Loop**: 跨 context window 保持状态，通过 EventLog 和 Checkpoint 实现长任务持久化  
**Milestone Loop**: 负责任务阶段性目标，串联 Plan/Approve/Execute/Verify  
**Plan Loop**: 生成并验证计划，不通过的计划不污染外层状态  
**Execute Loop**: LLM 驱动执行，遇到 Plan Tool 回到 Milestone Loop  
**Tool Loop**: WorkUnit 内部迭代，受 Envelope + DonePredicate 约束

#### 核心组件

```
dare_framework/
├── builder.py                 # AgentBuilder + Agent
├── core/                      # 核心状态与协议
│   ├── runtime.py             # AgentRuntime 五层循环
│   ├── models.py              # 核心数据结构
│   ├── interfaces.py          # 接口协议
│   └── errors.py              # 错误定义
├── components/                # 默认实现组件
│   ├── event_log.py           # LocalEventLog
│   ├── checkpoint.py          # FileCheckpoint
│   ├── tool_runtime.py        # ToolRuntime
│   ├── registries.py          # ToolRegistry / SkillRegistry
│   ├── policy_engine.py       # AllowAllPolicyEngine
│   ├── plan_generator.py      # DeterministicPlanGenerator
│   ├── validator.py           # SimpleValidator
│   ├── remediator.py          # NoOpRemediator
│   ├── context_assembler.py   # BasicContextAssembler
│   ├── model_adapter.py       # MockModelAdapter
│   ├── memory.py              # InMemoryMemory
│   ├── hooks.py               # NoOpHook
│   ├── mcp_client.py          # MCP SDK client adapters
│   └── mcp_toolkit.py         # MCPToolkit
└── validators/                # 预留：信任边界/覆盖验证
```

#### 核心接口（v1.3 UML A.1 + v1.1 Interface）

- Runtime/Orchestration: `IRuntime`, `IEventLog`, `ICheckpoint`, `IPolicyEngine`, `IPlanGenerator`, `IValidator`, `IRemediator`, `IContextAssembler`
- Tools/Skills: `IToolRuntime`, `IToolkit`, `ITool`, `ISkillRegistry`, `ISkill`
- Models/Composition: `IModelAdapter`, `IMemory`, `IHook`, `IMCPClient`

> MCP 客户端需要异步初始化；使用 `AgentBuilder.build_async()` 以加载 MCP 工具清单。

### Testing Strategy

#### 测试层次

1. **Unit Tests** (`tests/unit/`)
   - 每个模块的独立测试
   - Mock 所有外部依赖
   - 覆盖率目标: 90%+

2. **Integration Tests** (`tests/integration/`)
   - 组件间交互测试
   - 使用真实的 EventLog（本地文件）
   - 使用 Mock 的模型适配器

3. **E2E Tests** (`tests/e2e/`)
   - 完整的任务执行流程
   - 验证六步编排正确性

#### 测试命名

```python
def test_trust_boundary_derives_risk_level_from_registry():
    """TrustBoundary 应该从 Registry 派生 risk_level，忽略 LLM 填写的"""
    ...

def test_tool_runtime_rejects_unknown_tool():
    """ToolRuntime 应该拒绝未注册的工具"""
    ...
```

### Git Workflow

#### 分支策略

- `main` - 稳定分支，只接受 PR
- `develop` - 开发分支
- `feature/*` - 功能分支
- `fix/*` - 修复分支
- `openspec/*` - OpenSpec change proposal 分支

#### Commit 约定

使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(tool-runtime): add approval checking for high-risk tools
fix(event-log): ensure hash chain continuity
refactor(validators): extract common validation logic
docs(readme): add architecture diagram
test(coverage): add deterministic coverage validator tests
```

#### OpenSpec 工作流

所有重大变更必须通过 OpenSpec:

1. 创建 proposal: `/openspec:proposal`
2. 评审通过后实现: `/openspec:apply`
3. 部署后归档: `/openspec:archive`

详见 `openspec/AGENTS.md`

## Domain Context

### 信任边界

```
┌─────────────────────────────────────────────────────────────────┐
│                      Trust Boundary 信任边界                     │
├─────────────────────────────────────────────────────────────────┤
│  可信数据源（Ground Truth）           不可信数据源（需验证）       │
│  ─────────────────────────           ─────────────────────────  │
│  • Tool Registry 元数据               • LLM 生成的 Plan          │
│  • Policy Engine 规则                 • LLM 填写的 risk_level    │
│  • Event Log 历史记录                 • LLM 声称的 coverage      │
│  • External Validator 结果            • LLM 生成的 evidence      │
│  • Human Approval 签名                • 用户输入（需消毒）        │
└─────────────────────────────────────────────────────────────────┘
```

### 工具风险级别

| 级别 | 名称 | 含义 | 示例 |
|-----|-----|-----|-----|
| 1 | READ_ONLY | 只读，无副作用 | read_file, list_dir |
| 2 | IDEMPOTENT_WRITE | 幂等写入，可安全重试 | write_file, update_config |
| 3 | NON_IDEMPOTENT_EFFECT | 非幂等，需审批 | send_email, execute_command |
| 4 | COMPENSATABLE | 可补偿，有回滚能力 | create_pr (可 close) |

### 五个可验证闭环

每个安全机制都必须满足闭环：

```
输入是什么 → 不可变事实是什么 → 系统强制在哪里 → 证据落在哪里 → 如何复验
```

1. **WORM 一致性** - Event 写入后不可修改
2. **Sandbox 强度** - seccomp/网络隔离
3. **Coverage 确定性** - 集合运算 `requires ⊆ produces`
4. **Context 注入隔离** - 不可信内容有边界标记
5. **Token 权限绑定** - 令牌绑定 (agent_id, task_id)

## Important Constraints

### 安全约束

- **所有工具调用必须经过 ToolRuntime** - 不允许绕过
- **高风险工具需要审批** - `requires_approval: true`
- **LLM 输出永不可信** - 安全关键字段必须从可信源派生
- **Event Log 只追加** - 没有 update/delete 方法

### 性能约束

- **Tool 执行超时**: 默认 30 秒，可配置
- **Plan 生成超时**: 60 秒
- **最大补救次数**: 3 次

### 合规约束

- **审计日志保留**: 7 年（金融场景）
- **敏感数据令牌化**: 不进入模型上下文
- **操作可追溯**: 每个操作有 trace_id

## External Dependencies

### LLM Providers

- Anthropic Claude (primary)
- OpenAI GPT (fallback)
- 其他兼容 OpenAI API 的模型

### MCP SDK

- `mcp` Python SDK (https://github.com/modelcontextprotocol/python-sdk)

### 存储

- 本地文件系统 (MVP)
- PostgreSQL (生产)
- S3 with Object Lock (WORM 存储)

### 沙箱运行时

- Docker (代码执行隔离)
- seccomp (系统调用过滤)

## References

- [架构终稿评审 v1.3](/doc/design/Architecture_Final_Review_v1.3.md)
- [接口层设计 v1.1](/doc/design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md)
- [Anthropic Engineering 博客](/doc/design/anthropic-engineering.md)
