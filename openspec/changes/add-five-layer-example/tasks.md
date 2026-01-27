# Tasks: Add Five-Layer Coding Agent Example

## 1. 准备工作

- [ ] 1.1 创建 `examples/five-layer-coding-agent/` 目录结构
- [ ] 1.2 创建基础 `__init__.py` 文件
- [ ] 1.3 创建 `config.yaml` 配置文件模板
- [ ] 1.4 创建 `workspace/` 测试目录和示例文件

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
- [ ] 3.3 实现 `planners/openai_planner.py`（OpenAI Planner）
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

- [ ] 5.1 实现 `deterministic_agent.py`（确定性模式入口）
- [ ] 5.2 实现 Agent 组装逻辑
- [ ] 5.3 实现至少 3 个示例任务场景
- [ ] 5.4 实现 `openai_agent.py`（OpenAI 模式入口）
- [ ] 5.5 实现环境变量读取逻辑
- [ ] 5.6 实现配置文件加载逻辑
- [ ] 5.7 创建 `agent.py` 作为统一入口

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
- [ ] 7.5 添加 OpenAI 模式运行指南（包含环境变量）
- [ ] 7.6 添加示例任务场景说明
- [ ] 7.7 添加已知限制和未来工作说明
- [ ] 7.8 添加故障排查指南

## 8. 验证和优化

- [ ] 8.1 确保代码符合项目 lint 规范（Black, Ruff, mypy）
- [ ] 8.2 确保所有测试通过（pytest）
- [ ] 8.3 手动运行确定性模式验证端到端流程
- [ ] 8.4 手动运行 OpenAI 模式验证真实模型集成（如果有 API key）
- [ ] 8.5 检查所有文件的 docstrings 完整性
- [ ] 8.6 确保依赖项已添加到项目配置（如果需要）

## 9. 最终检查

- [ ] 9.1 运行 `openspec validate add-five-layer-example --strict`
- [ ] 9.2 确保 proposal、design、tasks、specs 都完整
- [ ] 9.3 在 Pull Request 中引用五层循环设计文档
- [ ] 9.4 更新项目根目录 README（如果需要）
- [ ] 9.5 标记 change 为 ready for review

## Dependencies

- ✅ **FiveLayerAgent**: 已实现（`dare_framework/agent/_internal/five_layer.py`）
- **External Tools**: pytest, pyyaml, openai（可选）

## Notes

- 每个 task 完成后应该运行相关测试确保没有引入 regression
- ✅ `FiveLayerAgent` 已实现，可以直接使用
- OpenAI 模式仅在提供 API key 时测试，CI 应该只运行确定性模式
- 参考 `FiveLayerAgent` 的实际接口：
  - 支持 `tools` 参数（IToolProvider）而不是 `tool_gateway`
  - 自动模式选择：Full Five-Layer / ReAct / Simple
  - `run()` 方法接受 `Task` 对象或字符串
