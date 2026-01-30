# 🎭 领导演示指南

## 快速启动

**最简单的演示方式（无需配置）**：

```bash
cd examples/five-layer-coding-agent
PYTHONPATH=../.. python interactive_cli.py
```

然后输入任务，例如：
- `Find all TODO comments`
- `Read sample.py and search for functions`
- `Search for function definitions`

输入 `quit` 退出。

## 演示脚本

### 1. 介绍背景 (30秒)

"这是我们基于 DARE Framework 开发的五层循环 Coding Agent。它采用了业界最佳实践的分层架构，确保 AI 的输出可控、可验证、可审计。"

### 2. 展示架构 (1分钟)

"我们的 Agent 有五层循环架构：
1. **Session Loop** - 跨 Context Window 的任务管理
2. **Milestone Loop** - 里程碑级别的目标跟踪和验证
3. **Plan Loop** - 计划生成和验证（失败不外泄）
4. **Execute Loop** - LLM 驱动的执行
5. **Tool Loop** - 工具调用的原子化执行

这个架构确保了每一步都是可验证、可回滚的。"

### 3. 实际演示 (2-3分钟)

**启动 CLI**：
```bash
PYTHONPATH=../.. python interactive_cli.py
```

**演示任务 1 - 简单搜索**：
```
You: Find all TODO comments
```

**讲解要点**：
- 👉 观察 Agent 如何"思考"任务
- 👉 看它如何生成执行计划
- 👉 注意每一层的验证过程
- 👉 工具调用是明确的、可审计的

**演示任务 2 - 多步骤任务**：
```
You: Read sample.py and search for functions
```

**讲解要点**：
- 👉 Agent 自动将任务分解为多个步骤
- 👉 每个步骤都有清晰的工具调用
- 👉 执行过程完全透明

### 4. 技术亮点 (1分钟)

**安全性**：
- ✅ LLM 输出不可信 - 所有关键参数从 ToolRegistry 派生
- ✅ 工具调用有风险级别管理（READ_ONLY, IDEMPOTENT_WRITE, NON_IDEMPOTENT_EFFECT）
- ✅ 计划验证失败不会影响主流程

**可靠性**：
- ✅ 状态外化 - 所有状态存 EventLog，不依赖模型记忆
- ✅ 外部验证 - "完成"由 Validator 判定，不是模型自说自话
- ✅ 增量执行 - 每步提交，可回滚

**可扩展性**：
- ✅ 工具可插拔 - 通过 IToolProvider 接口
- ✅ Planner 可替换 - 支持不同的规划策略
- ✅ Validator 可定制 - 根据业务需求验证

### 5. 实际应用场景 (30秒)

"这个框架可以用于：
- 📝 代码审查助手
- 🔍 代码分析和重构
- 🐛 Bug 定位和修复
- 📚 文档生成
- 🧪 测试用例生成

关键是它提供了一个**可控、可信、可审计**的 AI 执行环境。"

## 常见问题准备

### Q: 和 AutoGPT、LangChain 有什么区别？

**A**: 我们的核心差异是：
1. **安全第一** - LLM 输出不可信，关键字段从注册表派生
2. **分层验证** - 每一层都有独立的验证机制
3. **状态外化** - 不依赖模型记忆，所有状态外部管理

### Q: 能接入其他 LLM 吗？

**A**: 完全可以！我们支持：
- OpenRouter（支持 100+ 免费和付费模型）
- 自定义 ModelAdapter（实现接口即可）
- 本地模型（通过 OpenAI 兼容接口）

### Q: 性能如何？

**A**:
- 确定性模式：~1-2 秒（无 API 调用）
- OpenRouter 模式：~5-10 秒（取决于模型）
- 支持并发执行和批处理

### Q: 如何保证工具调用安全？

**A**:
1. **工具风险分级** - READ_ONLY, IDEMPOTENT_WRITE, NON_IDEMPOTENT_EFFECT
2. **参数验证** - ToolRegistry 强制参数模式
3. **执行沙箱** - 工具在受控环境执行（可选）
4. **审计日志** - 所有调用记录在 EventLog

## 演示技巧

### 准备工作
1. ✅ 提前测试一遍，确保环境正常
2. ✅ 准备好几个示例任务
3. ✅ 了解可能的输出和错误情况
4. ✅ 准备好架构图或 PPT（可选）

### 演示时
1. 📺 使用大字体（终端字号 18+）
2. 🎨 彩色输出很重要，确保终端支持 ANSI 颜色
3. ⏱️ 控制节奏，给观众时间理解每一步
4. 💬 边演示边讲解，不要只是操作

### 备选方案
如果现场网络/环境有问题：
- 提前录屏作为备份
- 使用 `scenarios.py all` 作为快速演示
- 准备静态的 PPT 展示架构和代码

## 进阶演示（如果时间充裕）

### 展示代码结构
```bash
tree -L 2 examples/five-layer-coding-agent/
```

### 展示工具定义
```bash
cat tools/__init__.py
```

### 展示 Planner 逻辑
```bash
cat planners/deterministic.py
```

### 运行测试场景
```bash
PYTHONPATH=../.. python scenarios.py all
```

## 总结话术

"通过刚才的演示，大家可以看到：

1. ✅ **透明性** - 每一步都清晰可见
2. ✅ **可控性** - 计划生成、验证、执行都有明确的控制点
3. ✅ **安全性** - 多层验证，工具风险分级
4. ✅ **可扩展性** - 组件化设计，易于定制

这就是我们的五层循环 Coding Agent。谢谢！"

---

**祝演示成功！** 🎉
