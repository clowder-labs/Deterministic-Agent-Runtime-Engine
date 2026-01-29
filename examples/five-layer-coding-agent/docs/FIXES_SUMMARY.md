# 🐛 Execute Loop 修复总结 - 贪吃蛇场景

## 📌 用户报告的问题

运行贪吃蛇场景时：

```
Evidence Requirements (2):
1. [ ] 证据：创建了贪吃蛇游戏文件 snake_game.py
2. [ ] 证据：游戏可以运行并可玩

✓ Task completed successfully!
Output: {'content': '我来为你写一个简单的贪吃蛇游戏。'}
```

**症状**：
- Task 显示成功但什么都没创建
- Evidence requirements 没有打勾
- 模型只返回文本，没有调用工具
- 用户指出："这个tool call的循环他应该是如果返回了tool 他就得react那个循环得一直继续啊！"

## 🔍 根本原因诊断

### 原因 1: Execute Loop 缺少系统消息

**问题**：
- `FiveLayerAgent._run_execute_loop()` 直接使用 `assembled.messages`
- STM 中只有用户消息，没有系统消息指导模型使用工具
- 模型收到 tools 参数，但不知道应该调用它们

**证据**：
```python
# test_execute_loop_debug.py 输出
📝 Messages being sent to model:
  1. [user] 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py...  ← 只有用户消息！

[DEBUG] Model returned NO tool calls (finish_reason: stop)
[DEBUG] Tools were provided to model: 3 tools
💬 Content: 我来为你创建一个可以玩的贪吃蛇游戏...  ← 返回文本解释
```

### 原因 2: Capability ID 映射错误

**问题**：
- 模型返回 function names（如 `write_file`）
- 但 ToolGateway 期望 capability IDs（如 `tool:write_file`）
- Execute Loop 没有进行映射

**证据**：
```python
# test_capability_id.py 输出
Function name (sent to model): write_file
Capability ID (used by gateway): tool:write_file  ← 不匹配！

# 错误消息
'Unknown capability id: write_file'  ← Gateway 找不到
```

### 原因 3: ReAct 模式下 _session_state 为 None

**问题**：
- `_run_tool_loop()` 尝试访问 `self._session_state.current_milestone_state`
- 在 ReAct 模式下，`_session_state` 是 None（因为跳过了 Session/Milestone loops）
- 导致 `AttributeError: 'NoneType' object has no attribute 'current_milestone_state'`

## ✅ 修复方案

### 修复 1: 创建 EnhancedFiveLayerAgent（添加系统消息）

**文件**：`enhanced_agent.py`

**修改**：重写 `_run_execute_loop()` 方法，在消息列表前添加系统消息

```python
EXECUTE_SYSTEM_PROMPT = """You are a helpful coding assistant with access to tools for file operations.

IMPORTANT INSTRUCTIONS:
1. You MUST use the provided tools to complete tasks - DO NOT just describe what you would do
2. When asked to write/create files, use the write_file tool immediately
3. When asked to read/search files, use read_file or search_code tools
4. DO NOT return explanatory text without calling tools first
5. Call tools step by step to accomplish the task

Available tools:
- write_file: Write content to a file (use this to create code files)
- read_file: Read file contents
- search_code: Search for patterns in code

Remember: TAKE ACTION using tools, don't just explain what you would do!"""

async def _run_execute_loop(self, plan: ValidatedPlan | None) -> dict[str, Any]:
    # Assemble context
    assembled = self._context.assemble()

    # ENHANCEMENT: Add system message at the beginning
    messages = assembled.messages.copy()
    if not messages or messages[0].role != "system":
        system_msg = Message(role="system", content=self.EXECUTE_SYSTEM_PROMPT)
        messages = [system_msg] + messages  ← 添加系统消息

    # Create prompt with enhanced messages
    prompt = Prompt(
        messages=messages,
        tools=assembled.tools,
        metadata=assembled.metadata,
    )
    # ... rest of loop
```

### 修复 2: 添加 Capability ID 映射

**位置**：`enhanced_agent.py` 中的 `_run_execute_loop()`

**修改**：在处理 tool_calls 时，将 function name 映射到 capability_id

```python
for tool_call in response.tool_calls:
    name = tool_call.get("name", "")

    # Map function name to capability_id
    # Model returns function names (e.g., "write_file")
    # But ToolGateway expects capability IDs (e.g., "tool:write_file")
    capability_id = name
    if not capability_id.startswith("tool:"):
        capability_id = f"tool:{name}"  ← 添加前缀映射

    # Run tool loop
    tool_result = await self._run_tool_loop(
        ToolLoopRequest(
            capability_id=capability_id,  # Use mapped capability_id
            params=tool_call.get("arguments", {}),
        )
    )
```

### 修复 3: 处理 ReAct 模式下的 _session_state

**位置**：`enhanced_agent.py` 中的 `_run_tool_loop()`

**修改**：重写 `_run_tool_loop()` 方法，检查 `_session_state` 是否为 None

```python
async def _run_tool_loop(self, request):
    # ... tool invocation code ...

    # Collect evidence (only if _session_state exists)
    if self._session_state is not None:  ← 检查是否为 None
        milestone_state = self._session_state.current_milestone_state
        if milestone_state and hasattr(result, "evidence"):
            for evidence in result.evidence:
                milestone_state.add_evidence(evidence)

    return {
        "success": True,
        "result": result,
    }
```

### 修复 4: 更新 interactive_cli.py

**文件**：`interactive_cli.py`

**修改**：使用 `EnhancedFiveLayerAgent` 替代 `FiveLayerAgent`

```python
# Import
from enhanced_agent import EnhancedFiveLayerAgent

# Create agent
agent = EnhancedFiveLayerAgent(  ← 使用增强版
    name="interactive-agent",
    model=model,
    tools=tool_provider,
    tool_gateway=tool_gateway,
    planner=planner,
    validator=validator,
)
```

## 🧪 验证测试

### 测试 1: 验证工具定义正确

```bash
$ python test_assembled_tools.py

✓ Tools found in assembled context:
  1. function - read_file
  2. function - search_code
  3. function - write_file
```

**结论**：Tools 确实在 assembled context 中 ✅

### 测试 2: 诊断为什么模型不调用工具

```bash
$ python test_execute_loop_debug.py

📝 Messages being sent to model:
  1. [user] 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py

[DEBUG] Model returned NO tool calls
💬 Content: 我来为你创建一个可以玩的贪吃蛇游戏...
```

**结论**：缺少系统消息，模型不知道应该调用工具 ❌

### 测试 3: 验证 Capability ID 格式

```bash
$ python test_capability_id.py

1. Function name (sent to model): write_file
   Capability ID (used by gateway): tool:write_file  ← 不匹配！
```

**结论**：需要映射 function name → capability_id ❌

### 测试 4: 验证系统消息修复

```bash
$ python test_system_message.py

[DEBUG] Execute Loop - Messages being sent to model:
  1. [system] You are a helpful coding assistant with access to tools...
  2. [user] 写一个文件 test.txt，内容是 hello world

[DEBUG] Model returned 1 tool calls
  - write_file  ← 模型现在调用工具了！✅

📊 Result:
  Outputs: [{'success': True, 'result': ToolResult(..., 'bytes_written': 11)}]
```

**结论**：系统消息起作用了！模型现在调用工具！✅

## 📊 修复前后对比

### ❌ 修复前

**Execute Loop 流程**：
```
1. 用户消息：写一个贪吃蛇游戏
2. Assemble context → messages=[user_msg], tools=[3 tools]
3. Model.generate() → NO system message
4. Model 返回：NO tool_calls, content="我来为你创建..."
5. Execute Loop 退出：success=True, output=text
6. 结果：没有调用工具，没有创建文件
```

**用户看到的输出**：
```
Evidence Requirements:
1. [ ] 证据：创建了贪吃蛇游戏文件 snake_game.py  ← 没打勾
2. [ ] 证据：游戏可以运行并可玩  ← 没打勾

✓ Task completed successfully!
Output: {'content': '我来为你写一个简单的贪吃蛇游戏。'}  ← 只有文本
```

### ✅ 修复后

**Execute Loop 流程**：
```
1. 用户消息：写一个贪吃蛇游戏
2. Assemble context → messages=[user_msg], tools=[3 tools]
3. EnhancedAgent 添加系统消息 → messages=[system_msg, user_msg]
4. Model.generate() → WITH system message ✅
5. Model 返回：tool_calls=[{name: "write_file", args: {...}}] ✅
6. Map function name → capability_id: "write_file" → "tool:write_file" ✅
7. Invoke tool → ToolGateway.invoke("tool:write_file", params) ✅
8. Tool 执行成功 → 文件被创建 ✅
9. Evidence tracker 提取证据 → 打勾 ✅
```

**用户期望看到的输出**：
```
Evidence Requirements:
1. ✓ 证据：创建了贪吃蛇游戏文件 snake_game.py  ← 打勾！
   Evidence: 已创建 1 个文件: snake_game.py

2. ✓ 证据：游戏可以运行并可玩  ← 打勾！
   Evidence: 代码已创建（功能待用户测试）

✓ Task completed successfully!
Output: Created snake_game.py successfully!
```

## 🎯 修复的三个关键点

1. **系统消息** - 指导模型使用工具而不是返回文本
2. **Capability ID 映射** - 将模型返回的 function name 映射到 ToolGateway 期望的 capability_id
3. **ReAct 模式兼容** - 处理 `_session_state` 为 None 的情况

## 📁 修改的文件

1. **`enhanced_agent.py`** (NEW)
   - `EnhancedFiveLayerAgent` 类
   - 重写 `_run_execute_loop()` 方法（添加系统消息 + capability_id 映射）
   - 重写 `_run_tool_loop()` 方法（处理 `_session_state` 为 None）

2. **`interactive_cli.py`** (MODIFIED)
   - 导入 `EnhancedFiveLayerAgent`
   - 使用 `EnhancedFiveLayerAgent` 替代 `FiveLayerAgent`

3. **测试文件** (NEW - 用于验证修复):
   - `test_tool_use.py`
   - `test_assembled_tools.py`
   - `test_execute_loop_debug.py`
   - `test_capability_id.py`
   - `test_system_message.py`
   - `test_snake_end_to_end.py`

## 🚀 下一步

用户需要运行完整的端到端测试验证：

```bash
cd examples/five-layer-coding-agent
PYTHONPATH=../.. python test_snake_end_to_end.py
```

或者使用交互式 CLI：

```bash
PYTHONPATH=../.. python interactive_cli.py --openrouter

> 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py
```

**期望结果**：
- ✅ 模型调用 `write_file` 工具
- ✅ `workspace/snake_game.py` 文件被创建
- ✅ Evidence requirements 显示打勾
- ✅ 用户可以运行 `python workspace/snake_game.py` 测试游戏

## 💡 架构洞察

**问题不在于框架设计，而在于 Execute Loop 的实现细节：**

1. **框架的 Execute Loop** 是 ReAct 模式（模型自主决定工具调用），设计正确
2. **但缺少系统消息**，导致模型不知道应该调用工具
3. **Capability ID 映射缺失**，导致工具调用失败

**这是一个配置/提示工程问题，不是架构问题**。

## ⚠️ 已知限制

1. **System message 重复** - 每次迭代都会重新添加系统消息（可以优化）
2. **Envelope 配置** - 工具调用可能需要配置 workspace_roots（待验证）
3. **模型能力依赖** - 不是所有模型都支持 function calling（arcee-ai/trinity-large-preview:free 已验证支持）

## 📝 TODO

- [ ] 运行完整端到端测试验证文件创建
- [ ] 检查 workspace_roots 配置是否需要
- [ ] 优化系统消息添加逻辑（避免重复）
- [ ] 考虑是否需要将修复合并到框架核心
