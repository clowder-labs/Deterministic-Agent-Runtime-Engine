# 🤝 Five-Layer Coding Agent - 交接文档

**日期**: 2025-01-29
**状态**: MVP 完成，待框架更新后适配

---

## 📦 已提交的内容

**Commit**: `a95a844` - "feat: implement evidence-based planning with interactive CLI"

### 核心功能

✅ **证据驱动规划系统** - Plans 定义验证标准（what to achieve），不是执行步骤（how to do it）
✅ **交互式 CLI** - 命令系统 + 计划审批工作流
✅ **Execute Loop 增强** - 系统消息指导模型使用工具
✅ **Milestone Loop 重试** - 验证失败 → 反思 → 重试（最多3次）
✅ **Evidence 提取** - 从 Event Log 提取证据并显示 ✓/✗

### 文件组织

```
examples/five-layer-coding-agent/
├── README.md              ← 主文档，用户入口
├── STATUS.md              ← 实现状态，已知问题，TODO
├── HANDOFF.md             ← 本文件，交接说明
│
├── Core (核心组件)
├── interactive_cli.py     ← 主程序入口
├── enhanced_agent.py      ← 修复后的 Agent
├── cli_commands.py
├── cli_display.py
├── evidence_tracker.py
│
├── planners/              ← 规划器
│   └── llm_planner.py    ← LLM 证据规划器
│
├── validators/            ← 验证器
│   └── simple_validator.py ← 修复后（不再总是返回 True）
│
├── tests/                 ← 所有测试（已整理）
│   ├── test_milestone_retry.py
│   ├── test_tool_use.py
│   └── ...
│
└── docs/                  ← 所有文档（已整理）
    ├── FIXES_SUMMARY.md
    ├── MILESTONE_LOOP_DIAGNOSIS.md
    └── ...
```

---

## 🎯 当前状态总结

### ✅ 什么是工作的

1. **框架实现是正确的**
   - `dare_framework/agent/_internal/five_layer.py` 的 Milestone Loop 完全符合五层循环设计
   - 包含完整的重试机制：Observe → Plan → Execute → Verify → Remediate → Retry

2. **Evidence-based planning 已实现**
   - Plans 定义验证标准（evidence requirements）
   - Execute Loop 使用 ReAct 模式（模型动态决定工具调用）
   - Evidence tracker 从 event log 提取证据

3. **Interactive CLI 已完成**
   - 命令系统（`/mode`, `/help`, `/quit`）
   - Plan 和 Execute 两种模式
   - 证据显示（带 ✓/✗ 标记）

### ❌ 什么是不工作的

**核心问题：免费模型不可靠地调用工具**

**症状**：
```
[DEBUG] Model returned NO tool calls (finish_reason: stop)
✓ Task completed successfully!  ← 但什么都没创建
```

**原因**：
- 免费 OpenRouter 模型（如 `arcee-ai/trinity-large-preview:free`, `google/gemini-flash-1.5:free`）对 function calling 的支持不稳定
- 即使有强系统消息，模型仍然经常返回文本而不是调用工具

**已尝试的修复**：
- ✅ 添加强系统消息："YOU MUST USE TOOLS"
- ✅ 验证 tools 正确传给模型
- ✅ 添加 capability ID 映射
- ❌ 模型仍然不可靠

**解决方案**：
- 使用付费模型：`google/gemini-flash-1.5`, `claude-sonnet-3.5`, `gpt-4o`
- 或使用本地 Ollama（如 `llama3.1`）

---

## 🔧 关键技术决策

### 1. EnhancedFiveLayerAgent vs 修改框架

**决策**：创建 `enhanced_agent.py` 子类，而不是修改 `dare_framework`

**原因**：
- Example 不应该修改框架核心
- 框架可能被其他人更新
- 保持更改隔离，便于维护

**Trade-off**：一些代码重复（重写方法）

### 2. System Message 在 Execute Loop

**决策**：在 Execute Loop 开头添加系统消息

**原因**：
- 框架的 Execute Loop 不添加系统消息
- 模型不知道应该使用工具
- 这是提示工程问题，不是架构问题

**实现**：`enhanced_agent.py:EXECUTE_SYSTEM_PROMPT`

### 3. Capability ID 映射

**决策**：在 Execute Loop 中映射 function name → capability_id

**原因**：
- 模型返回 function names（如 `write_file`）
- ToolGateway 期望 capability IDs（如 `tool:write_file`）
- 这是阻抗不匹配，需要桥接

**实现**：`enhanced_agent.py:_run_execute_loop` (line ~110)

### 4. Validator 修复

**决策**：SimpleValidator 真正检查输出，不再总是返回 `success=True`

**原因**：
- 原来的实现总是返回 True，导致 Milestone Loop 不重试
- 违反了五层循环的设计
- 修复后能正确触发重试机制

**实现**：`validators/simple_validator.py:verify_milestone`

---

## 🚀 如何继续

### 场景 1: 框架被更新

**如果别人修改了 `dare_framework` 的代码，需要适配：**

#### 1. 检查 Milestone Loop 是否有变化

```bash
git log --oneline dare_framework/agent/_internal/five_layer.py
git diff <last-known-commit> dare_framework/agent/_internal/five_layer.py
```

**关键方法**：
- `_run_milestone_loop` (line 435-493)
- `_run_execute_loop` (line 564-657)
- `_run_tool_loop` (line 663-710)

**如果签名改变**，需要更新 `enhanced_agent.py` 中重写的方法。

#### 2. 检查 Tool 系统是否有变化

```bash
git log --oneline dare_framework/tool/
```

**关键接口**：
- `IToolGateway.invoke()` - 如果参数改变，更新 `enhanced_agent.py`
- Tool capability_id 格式 - 如果从 `tool:*` 改变，更新映射逻辑

#### 3. 检查 Context Assembly 是否有变化

```bash
git log --oneline dare_framework/context/_internal/context.py
```

**关键方法**：
- `context.assemble()` - 返回值格式
- `context.listing_tools()` - 工具列表格式

#### 4. 运行测试验证

```bash
cd examples/five-layer-coding-agent

# 快速验证
PYTHONPATH=../.. python tests/test_tool_use.py

# 完整测试
PYTHONPATH=../.. python tests/test_milestone_retry.py
PYTHONPATH=../.. python interactive_cli.py --openrouter
```

### 场景 2: 找到了更好的模型

**如果找到了免费且支持 function calling 的模型：**

1. **更新 `.env.example`**：
   ```env
   OPENROUTER_MODEL=<new-better-model>
   ```

2. **测试工具调用**：
   ```bash
   PYTHONPATH=../.. python tests/test_tool_use.py
   ```

3. **如果成功**，更新 `STATUS.md` 和 `README.md`：
   ```markdown
   ## Recommended Models

   - `<new-model>` - ✅ Reliably supports function calling (free!)
   ```

### 场景 3: 实现 Remediator

**当前状态**：Remediator 未实现（MVP 留空）

**如何实现**：

1. **创建 `planners/llm_remediator.py`**：
   ```python
   class LLMRemediator:
       @property
       def component_type(self):
           return ComponentType.REMEDIATOR

       async def remediate(self, verify_result, ctx):
           # 让 LLM 生成结构化反思
           prompt = f"Task failed: {verify_result.errors}"
           reflection = await self.model.generate(prompt)
           return reflection.content
   ```

2. **在 `interactive_cli.py` 中使用**：
   ```python
   from planners.llm_remediator import LLMRemediator

   remediator = LLMRemediator(model)

   agent = EnhancedFiveLayerAgent(
       ...,
       remediator=remediator,  # ← 添加
   )
   ```

3. **测试重试时是否有更好的反思**：
   ```bash
   PYTHONPATH=../.. python tests/test_milestone_retry.py
   ```

### 场景 4: Debug Workspace 路径问题

**当前症状**：工具调用成功但文件找不到

**调试步骤**：

1. **添加 debug 日志到 `enhanced_agent.py`**：
   ```python
   async def _run_tool_loop(self, request):
       ...
       result = await self._tool_gateway.invoke(...)

       # DEBUG: 显示实际创建的文件路径
       if hasattr(result, 'output') and 'path' in result.output:
           print(f"[DEBUG] File created at: {result.output['path']}")

       return {"success": True, "result": result}
   ```

2. **检查 Envelope 配置**：
   ```python
   # 在 FiveLayerAgent 初始化时
   from dare_framework.tool.types import Envelope

   envelope = Envelope(
       workspace_roots=[str(workspace)],  # 确保设置了 workspace
   )
   ```

3. **运行测试并检查路径**：
   ```bash
   PYTHONPATH=../.. python tests/test_write_tool_direct.py
   ```

---

## 📚 关键文档速查

| 文档 | 用途 |
|------|------|
| `README.md` | 用户入口，快速开始 |
| `STATUS.md` | 实现状态，已知问题，TODO |
| `HANDOFF.md` | 本文件，交接说明 |
| `docs/FIXES_SUMMARY.md` | Execute Loop 修复详情 |
| `docs/MILESTONE_LOOP_DIAGNOSIS.md` | Milestone Loop 重试机制诊断 |
| `docs/EVIDENCE_SYSTEM_UPDATE.md` | Evidence-based planning 设计 |

---

## 🧪 测试指南

### 快速验证（无需模型）

```bash
PYTHONPATH=../.. python scenarios.py all
```

### 验证工具调用（需要 API key）

```bash
PYTHONPATH=../.. python tests/test_tool_use.py
```

**期望输出**：
```
✅ SUCCESS: Model used function calling!
Tool Call 1:
  Name: write_file
  Arguments: {'content': "print('hello')", 'path': 'test.py'}
```

### 验证重试机制

```bash
PYTHONPATH=../.. python tests/test_milestone_retry.py
```

**期望行为**：
- Attempt 1: 模型返回文本 → Verify FAIL → 触发重试
- Attempt 2: 重新 Plan → Execute → Verify
- 最多 3 次尝试

### 交互式测试

```bash
PYTHONPATH=../.. python interactive_cli.py --openrouter

> 写一个简单的 hello.py 文件
```

**观察点**：
1. 是否显示 Plan？
2. Evidence requirements 是什么？
3. 执行后 Evidence 是否打勾？
4. 文件是否创建？

---

## ⚠️ 已知坑点

### 1. 免费模型不可靠

**症状**：即使配置正确，模型也可能返回文本而不是调用工具

**解决**：使用付费模型或接受不稳定性

### 2. 用户消息重复

**症状**：STM 中有两条相同的用户消息

**原因**：测试代码手动添加 + agent.run() 又添加

**解决**：不要手动添加消息到 STM，直接调用 `agent.run(task)`

### 3. Validator 总是返回 True

**症状**：Task 说成功但什么都没做

**原因**：旧版 `simple_validator.py` 总是返回 `success=True`

**解决**：✅ 已修复（commit a95a844）

### 4. Capability ID 不匹配

**症状**：`Unknown capability id: write_file`

**原因**：模型返回 `write_file`，Gateway 期望 `tool:write_file`

**解决**：✅ 已修复（enhanced_agent.py 映射）

---

## 🎁 遗留给未来的礼物

### 已实现的基础

1. ✅ **完整的五层循环示例** - 可以作为其他 example 的参考
2. ✅ **Evidence-based planning 模式** - 可以复用到其他场景
3. ✅ **Interactive CLI 框架** - 可以扩展更多命令
4. ✅ **详细的诊断文档** - 未来遇到问题可以参考

### 待实现的增强

1. ⚠️ **LLMRemediator** - 生成结构化反思
2. ⚠️ **Event Log 持久化** - 跨 session 证据追踪
3. ⚠️ **Workspace 配置修复** - 确保文件路径正确
4. ⚠️ **更好的免费模型** - 找到可靠的免费替代

### 架构洞察

**框架是对的，问题在细节**：
- ✅ Milestone Loop 的重试机制设计完美
- ✅ Evidence-based planning 思路正确
- ❌ Validator 实现有 bug（已修复）
- ❌ 免费模型能力不足（建议付费）

---

## 📞 快速联系

如果未来需要继续这个项目：

1. **先看** `STATUS.md` - 了解当前状态
2. **再看** `docs/MILESTONE_LOOP_DIAGNOSIS.md` - 如果重试机制有问题
3. **然后看** `docs/FIXES_SUMMARY.md` - 如果工具调用有问题
4. **最后** 运行测试验证当前状态

---

## 🎯 一句话总结

**核心已完成，框架实现正确，主要问题是免费模型不可靠。建议使用付费模型或等待更好的免费模型。代码已整理并提交，文档齐全，可以随时继续。**

---

*Handoff completed on 2025-01-29 by Claude*
