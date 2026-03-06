## Context

现有 model domain 的默认适配器仅覆盖 OpenAI / OpenRouter。用户需要“完整新增”Anthropic adapter，而不是在已有 adapter 上做兼容分支。该改动涉及模型调用层、默认 adapter 管理器、CLI 诊断链路和文档契约更新，属于跨模块变更。

## Goals / Non-Goals

**Goals:**
- 提供独立 `AnthropicModelAdapter`，并保持与现有 `IModelAdapter` 契约一致。
- 模型名仅做直传：由 `Config.llm.model` 或 `ANTHROPIC_MODEL` 提供，不维护硬编码别名映射。
- 支持 tool calling 对话回放链路：assistant `tool_use` 与 tool `tool_result`。
- 在 CLI doctor 中加入 `anthropic` adapter 的配置与依赖可观测性。

**Non-Goals:**
- 不改造 OpenAI / OpenRouter adapter 的内部逻辑。
- 不实现 streaming 接口。
- 不新增多 provider 自动路由策略。

## Decisions

1. **独立实现 Anthropic adapter**
- Decision: 新建 `dare_framework/model/adapters/anthropic_adapter.py`，不复用 `openrouter_adapter.py`。
- Rationale: 用户要求“完整新增”；Anthropic Messages API 的 message/tool 结构也与 OpenAI-compatible 接口不同。
- Alternative considered: 在 OpenRouter adapter 内新增 Anthropic 分支，违背隔离要求且会放大耦合。

2. **模型名来源固定为配置/环境变量**
- Decision: 适配器不做模型别名转换，仅接受 `Config.llm.model` 或 `ANTHROPIC_MODEL` 的直接值。
- Rationale: 避免“新模型发布 -> 需要改框架代码”耦合，模型升级由配置侧完成。
- Alternative considered: 内置别名映射；该方案会引入版本漂移与维护负担。

3. **序列化策略对齐 Anthropic Messages API**
- Decision: `system` 消息单独抽取到 `system` 字段；assistant 历史 tool call 序列化为 `tool_use` block；tool 回包序列化为 user `tool_result` block。
- Rationale: 与 Anthropic 官方 tool-use 协议一致，保证多轮工具调用可追踪。

4. **CLI doctor 扩展 anthropic 诊断**
- Decision: 新增 `ANTHROPIC_API_KEY` 来源检查和 `anthropic` SDK 依赖检查。
- Rationale: 让运行前诊断与新增 adapter 保持一致，避免误判“unsupported adapter”。

## Risks / Trade-offs

- [Risk] Anthropic SDK 未安装导致运行期失败。  
  Mitigation: doctor 增加依赖告警；adapter 在 `_build_client` 处抛出明确 ImportError。
- [Risk] Anthropic API block 字段未来变化导致解析漂移。  
  Mitigation: 解析函数统一封装 `_extract_*`，并以单元测试锚定。
- [Risk] 用户未配置模型名会导致启动失败。  
  Mitigation: 在 adapter 初始化阶段给出明确错误信息；README 与示例文件提供最小配置模板。

## Migration Plan

1. 添加 Anthropic adapter 与单测（先红后绿）。
2. 接入 manager/export/doctor 并补齐相关测试。
3. 更新设计文档与 client 使用文档。
4. 运行定向测试验证新增能力。

Rollback:
- 若出现兼容问题，可仅回退 `default_model_adapter_manager.py` 中 `anthropic` 分支和新增 adapter 文件，不影响既有 `openai/openrouter` 路径。
