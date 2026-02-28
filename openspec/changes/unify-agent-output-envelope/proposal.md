## Why

当前 `SimpleChatAgent`、`ReactAgent`、`DareAgent` 返回的 `RunResult.output` 形状不一致（字符串、字典、列表混合），上层消费侧需要分支解析，导致接口复杂且容易出现类型漂移。  
需要将输出形状收敛为统一 envelope，确保调用方和序列化通道可稳定消费。

## What Changes

- 统一 `RunResult.output` 为 envelope 结构：`{"content": str, "metadata": dict, "usage": dict | None}`。
- `SimpleChatAgent`、`ReactAgent`、`DareAgent` 的 `execute(...)` 返回统一结构。
- 保持 `RunResult.output_text` 与 `output.content` 对齐，作为展示层稳定字段。
- 增加单元测试覆盖三类 agent 的输出契约与兼容行为。
- 更新设计文档与 TODO 证据闭环。  
- **BREAKING**: `RunResult.output` 不再返回原始字符串/非 envelope 结构。

## Capabilities

### New Capabilities
- `run-result-output-envelope`: 定义并约束 agent 运行结果的统一输出 envelope。

### Modified Capabilities
- `core-runtime`: 运行时结果契约从“任意 output”收敛为统一 envelope 输出。

## Impact

- 代码影响：
  - `dare_framework/agent/simple_chat.py`
  - `dare_framework/agent/react_agent.py`
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/_internal/output_normalizer.py`（复用/扩展）
  - 相关单元测试与文档 TODO
- API 影响：`RunResult.output` 数据形状变化（breaking）。
- 依赖影响：无新增外部依赖。
