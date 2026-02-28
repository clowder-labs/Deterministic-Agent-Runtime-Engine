## Why

`DareAgent` 当前单文件承载 Session/Milestone/Execute/Tool 多层编排，文件体量和职责耦合过高，导致变更回归面大、定位成本高、单元测试难以精准覆盖。A-101 需要把核心循环按职责拆分为可独立测试模块，并保持外部行为不变。

## What Changes

- 将 `dare_framework/agent/dare_agent.py` 的核心循环按职责拆分为独立内部模块：
  - `session_orchestrator`
  - `milestone_orchestrator`
  - `execute_engine`
  - `tool_executor`
- `DareAgent` 保留对外 API、依赖注入、顶层状态转移与组装逻辑；编排细节下沉到上述内部模块。
- 为拆分后的核心循环新增针对性单测，覆盖成功/失败路径与关键策略分支，确保不依赖完整 Agent 集成路径也可验证。
- 回写 `docs/design/modules/agent/TODO.md` 与 `docs/design/TODO_INDEX.md` 的 A-101 状态与证据。

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `core-runtime`: 增加运行时编排模块化边界与行为等价性要求，确保循环实现可分层替换且不改变既有运行语义。

## Impact

- Affected code:
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/_internal/*` (new orchestrator/executor modules)
  - `tests/unit/test_dare_agent_*.py` (targeted unit tests)
- Affected docs:
  - `docs/design/modules/agent/TODO.md`
  - `docs/design/TODO_INDEX.md`
- Compatibility:
  - No public API changes expected.
  - Runtime behavior should remain equivalent; deviations must be covered by regression tests.
