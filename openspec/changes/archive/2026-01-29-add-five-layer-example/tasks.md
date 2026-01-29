# Tasks: Add Five-Layer Coding Agent Example

## 1. 准备工作

- [ ] 1.1 创建 `examples/five-layer-coding-agent/` 目录结构
- [ ] 1.2 创建基础 `__init__.py` 文件
- [ ] 1.3 创建 `.env.example` 环境变量配置模板
- [ ] 1.4 确认 `.gitignore` 包含 `.env` 规则（不提交 API key）
- [ ] 1.5 创建 `workspace/` 测试目录和示例文件

## 2. 工具实现

- [ ] 2.1 实现 `tools/read_file.py`（读取文件工具）
- [ ] 2.2 实现 `tools/write_file.py`（写入文件工具）
- [ ] 2.3 实现 `tools/search_code.py`（代码搜索工具）
- [ ] 2.4 实现 `tools/run_tests.py`（运行测试工具）
- [ ] 2.5 实现 `tools/edit_file.py`（编辑文件工具）
- [ ] 2.6 创建 `tools/__init__.py` 并导出所有工具
- [ ] 2.7 为每个工具编写单元测试（`tests/test_tools.py`）

## 3. Planner 实现

- [ ] 3.1 实现 `planners/deterministic.py`（确定性 Planner）
- [ ] 3.2 创建测试用的预定义计划
- [ ] 3.3 实现 `planners/openrouter_planner.py`（OpenRouter Planner）
- [ ] 3.4 实现计划解析逻辑
- [ ] 3.5 创建 `planners/__init__.py` 并导出 Planners
- [ ] 3.6 为 Deterministic Planner 编写单元测试

## 4. Validator 实现

- [ ] 4.1 实现 `validators/simple_validator.py`（简单验证器）
- [ ] 4.2 实现 `validate_plan` 方法（计划验证）
- [ ] 4.3 实现 `verify_milestone` 方法（里程碑验证）
- [ ] 4.4 创建 `validators/__init__.py` 并导出 Validator
- [ ] 4.5 为 Validator 编写单元测试

## 5. Agent 实现

- [ ] 5.1 实现 `model_adapters/openrouter.py`（OpenRouter ModelAdapter）
- [ ] 5.2 实现 `deterministic_agent.py`（确定性模式入口）
- [ ] 5.3 实现 Agent 组装逻辑（使用 FiveLayerAgent）
- [ ] 5.4 实现至少 3 个示例任务场景
- [ ] 5.5 实现 `openrouter_agent.py`（OpenRouter 模式入口）
- [ ] 5.6 实现环境变量读取逻辑（从 .env 加载）
- [ ] 5.7 创建 `agent.py` 作为统一入口（模式选择）
- [ ] 5.8 **重要**：确认 .env 文件不在 git 追踪中

## 6. 集成测试

- [ ] 6.1 编写 `tests/test_deterministic_agent.py`（端到端测试）
- [ ] 6.2 测试单里程碑任务完成
- [ ] 6.3 测试多里程碑任务完成
- [ ] 6.4 测试计划验证失败重试
- [ ] 6.5 测试工具执行错误处理
- [ ] 6.6 测试 Tool Loop 的 DonePredicate 机制
- [ ] 6.7 确保所有测试通过

## 7. 文档编写

- [ ] 7.1 编写 `README.md` - 项目介绍和目标
- [ ] 7.2 添加架构说明和五层循环图示
- [ ] 7.3 添加目录结构说明
- [ ] 7.4 添加确定性模式运行指南
- [ ] 7.5 添加 OpenRouter 模式运行指南（包含 .env 配置步骤）
- [ ] 7.6 添加 OpenRouter 免费模型推荐列表
- [ ] 7.7 添加示例任务场景说明
- [ ] 7.8 添加已知限制和未来工作说明
- [ ] 7.9 添加故障排查指南
- [ ] 7.10 **重要**：在 README 中明确说明不要提交 .env 文件

## 8. 验证和优化

- [ ] 8.1 确保代码符合项目 lint 规范（Black, Ruff, mypy）
- [ ] 8.2 确保所有测试通过（pytest）
- [ ] 8.3 手动运行确定性模式验证端到端流程
- [ ] 8.4 手动运行 OpenRouter 模式验证真实模型集成
- [ ] 8.5 测试免费模型：`xiaomi/mimo-v2-flash:free`
- [ ] 8.6 检查所有文件的 docstrings 完整性
- [ ] 8.7 确保依赖项已添加到项目配置（`openai` SDK for OpenRouter）
- [ ] 8.8 **安全检查**：确认没有硬编码 API key
- [ ] 8.9 **安全检查**：确认 .env 文件在 .gitignore 中

## 9. 最终检查

- [ ] 9.1 运行 `openspec validate add-five-layer-example --strict`
- [ ] 9.2 确保 proposal、design、tasks、specs 都完整
- [ ] 9.3 在 Pull Request 中引用五层循环设计文档
- [ ] 9.4 更新项目根目录 README（如果需要）
- [ ] 9.5 标记 change 为 ready for review

## Dependencies

- ✅ **FiveLayerAgent**: 已实现（`dare_framework/agent/_internal/five_layer.py`）
- **External Tools**:
  - `pytest` - 测试框架
  - `python-dotenv` - 环境变量加载
  - `openai` - OpenAI SDK（用于 OpenRouter API 调用）

## Environment Setup

测试时需要配置 `.env` 文件：
```bash
# Copy template
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-...
# OPENROUTER_MODEL=xiaomi/mimo-v2-flash:free
```

**⚠️ 重要安全提醒**：
- 永远不要提交 `.env` 文件到 git
- 已在 `.gitignore` 中配置忽略 `.env`
- 只提交 `.env.example` 模板文件

## Notes

- 每个 task 完成后应该运行相关测试确保没有引入 regression
- ✅ `FiveLayerAgent` 已实现，可以直接使用
- OpenRouter 模式仅在提供 API key 时测试，CI 应该只运行确定性模式
- 参考 `FiveLayerAgent` 的实际接口：
  - 支持 `tools` 参数（IToolProvider）而不是 `tool_gateway`
  - 自动模式选择：Full Five-Layer / ReAct / Simple
  - `run()` 方法接受 `Task` 对象或字符串
- **OpenRouter 配置**：
  - 使用免费模型测试：`xiaomi/mimo-v2-flash:free`
  - 兼容 OpenAI SDK，无需额外适配
  - Base URL: `https://openrouter.ai/api/v1`
- **安全最佳实践**：
  - 使用环境变量管理 API key
  - 不要硬编码任何敏感信息
  - 确保 `.env` 在 `.gitignore` 中
