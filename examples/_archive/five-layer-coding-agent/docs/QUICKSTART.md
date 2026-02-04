# 🚀 快速开始 - 5 分钟上手

## 步骤 1: 克隆代码（如果还没有）

```bash
git clone <repository>
cd dare-framework
```

## 步骤 2: 进入示例目录

```bash
cd examples/five-layer-coding-agent
```

## 步骤 3: 运行演示！

```bash
PYTHONPATH=../.. python scenarios.py all
```

就这么简单！🎉

## 你将看到什么

```
======================================================================
📖 Scenario 1: Read and Search
======================================================================
Task: Read sample.py and find TODO comments

[DEBUG] Verifying milestone...

✓ Result: Success=True

======================================================================
🔍 Scenario 2: Find All TODOs
======================================================================
...

======================================================================
🔬 Scenario 3: Analyze Code Structure
======================================================================
...

======================================================================
✓ Scenario(s) completed
======================================================================
```

## 这演示了什么？

- ✅ **Five-Layer Loop** - 五层循环架构完整执行
- ✅ **Tool Execution** - ReadFile, SearchCode 等工具调用
- ✅ **Plan Validation** - 计划验证和执行
- ✅ **Milestone Verification** - 里程碑验证机制
- ✅ **No API Key Needed** - 确定性模式，无需配置

## 下一步？

### 想体验交互式对话？

最适合演示和理解 Agent 工作流程：

```bash
PYTHONPATH=../.. python interactive_cli.py
```

输入任务，看 Agent 实时规划和执行！

### 想体验真实 LLM？

```bash
# 1. 复制配置
cp .env.example .env

# 2. 编辑 .env，添加你的 OpenRouter API key
nano .env

# 3. 运行
PYTHONPATH=../.. python openrouter_agent.py
```

免费 API key 获取：https://openrouter.ai/

### 想了解更多？

- 📖 [完整文档](README.md)
- 📝 [详细使用指南](USAGE.md)
- 🏗️ [架构设计](../../docs/design/Architecture.md)

### 想定制场景？

编辑 `scenarios.py`，添加你自己的任务！

```python
async def my_custom_scenario():
    plan = ProposedPlan(
        plan_description="Your task",
        steps=[
            ProposedStep(
                step_id="step1",
                capability_id="read_file",
                params={"path": "your_file.py"},
            ),
        ],
    )

    agent = create_agent(plan)
    result = await agent.run(Task(description="Custom", task_id="custom"))
    print(f"Result: {result.success}")
```

## 遇到问题？

### ImportError: No module named 'dare_framework'

确保使用 `PYTHONPATH=../..` 前缀：
```bash
PYTHONPATH=../.. python scenarios.py all
```

### 其他问题

查看 [USAGE.md](USAGE.md) 的故障排查部分

## 反馈和贡献

- 🐛 发现 Bug？提 Issue
- 💡 有想法？提 PR
- ❓ 有疑问？查看文档或提问

---

**Happy Coding! 🎉**
