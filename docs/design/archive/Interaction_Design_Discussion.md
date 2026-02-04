# DARE Framework 交互设计讨论总结

> 日期: 2026-01-27
> 状态: 待进一步讨论

---

## 1. 问题背景

### 1.1 核心诉求
设计一个统一的交互机制，让基于 DARE Framework 开发的 Agent（无论是 CLI、Web 还是 IDE 插件形态）都能以一致的方式处理：
- 用户输入
- LLM 输出/思考过程
- 工具调用状态
- 修改内容呈现
- 用户授权

### 1.2 现有基础
- `IExtensionPoint` / `IHook`：生命周期事件的观察机制（单向、best-effort）
- `IExecutionControl`：HITL 控制面（`pause/resume/wait_for_human`）

---

## 2. 设计演进过程

### 2.1 方案一：Notify-Request 模型
**思路**：将交互分为"通知"（单向广播）和"请求"（阻塞等待）。

```python
class ITerminalAdapter(Protocol):
    async def notify(self, event: AgentEvent) -> None: ...
    async def request(self, request: InteractionRequest) -> InteractionResponse: ...
```

**问题**：`notify` 本质上就是 Hook，造成概念冗余。

---

### 2.2 方案二：面向 Agent 行为的抽象
**思路**：按 ReAct 的"思考-行动-观察"语义命名方法。

```python
class IInteractionSurface(Protocol):
    async def on_thought(self, content: str) -> None: ...
    async def on_action(self, tool_name: str) -> None: ...
    async def on_observation(self, result: Any) -> None: ...
    async def confirm(self, prompt: str) -> bool: ...
    async def ask(self, prompt: str) -> str: ...
```

**问题**：`on_xxx` 依然和 Hook 高度相似。

---

### 2.3 方案三：双轨交互 (Dual-Track)
**思路**：
- **输出轨**：完全回归 Hook 系统，保持内核纯净。
- **输入轨**：引入 `IInputChannel`，处理同步请求、异步缓冲和即时中断。

```python
class IInputChannel(Protocol):
    async def request_input(self, prompt: str) -> InteractionResponse: ...
    def push_info(self, content: str) -> None: ...
    def consume_buffered_info(self) -> list[str]: ...
    def trigger_interrupt(self, signal: InterruptSignal) -> None: ...
```

**问题**：需要在编排流程中显式调用这些方法，导致"别扭感"。

---

### 2.4 方案四：中断感知执行器 (Interruptible Invoker)
**思路**：用 `invoke_with_interrupt(channel, coro)` 包装长耗时任务，统一处理中断。

```python
result, interrupted = await invoke_with_interrupt(
    self.channel, 
    self.model.generate(prompt)
)
```

**问题**：仍需显式处理各种交互场景（授权、选择、输入），扩展性不足。

---

## 3. 终极方案提议：透明交互架构

### 3.1 核心理念
将交互从编排层**剥离**，下沉到**能力层 (Tool)** 和**内核层 (Gateway/Policy)**。

### 3.2 三种交互归类

| 交互类型 | 处理层 | 机制 | 编排层感知 |
|---------|-------|------|-----------|
| **确定性交互** | 能力层 | 定义 `ask_user`、`request_file` 等**交互类工具** | Agent 通过 ReAct 自行决定调用，编排层只看到 `gateway.invoke()` |
| **授权拦截** | 内核层 | `IToolGateway` 根据工具风险等级自动触发 `ExecutionControl.pause()` | 编排层完全透明，只是 `await` 变长了 |
| **运行时注入** | 上下文层 | 用户输入存入 `Context` Buffer，通过 `assemble()` 自动合并 | 编排层无需任何 `if` 判断 |

### 3.3 理想的编排代码

```python
async def _run_execute_loop(self):
    while not finished:
        # 1. 组装上下文（自动包含异步注入的用户指令）
        assembled = self.context.assemble() 
        
        # 2. 生成响应
        response = await self.model.generate(assembled)
            
        # 3. 处理工具调用（交互/授权/业务工具统一处理）
        for tool_call in response.tool_calls:
            result = await self.gateway.invoke(tool_call)
            self.context.add_observation(result)
```

### 3.4 优点
1. **场景不遗漏**：增加交互场景 = 增加 Tool 或配置 Policy，不改编排代码。
2. **扩展性强**：符合 DARE 的"LLM 驱动、外部可验证"设计理念。
3. **代码自然**：编排逻辑是一条直线，没有交互分支。

---

## 4. 待讨论问题

1. **交互类工具的定义**：如何标准化 `ask_user`、`confirm_action` 等内置工具的接口？
2. **授权策略配置**：如何在 `IToolGateway` 中配置不同工具的授权级别？
3. **Context Buffer 的生命周期**：异步注入的信息何时过期？如何避免上下文污染？
4. **复杂选择场景**：当 LLM 生成结构化选项时，如何触发"交互类工具"？

---

## 5. 参考资料

- [OpenAI Codex CLI](https://github.com/openai/codex)：采用可配置的权限模式（suggest-only → 全自动）
- [Claude Code](https://docs.anthropic.com/claude-code)：单线程主循环 + 权限系统 + HITL 暂停点
- DARE 现有接口：`IHook`、`IExtensionPoint`、`IExecutionControl`、`IToolGateway`
