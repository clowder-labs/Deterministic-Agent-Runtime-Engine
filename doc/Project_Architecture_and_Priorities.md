# DARE Framework：架构现状与优先级清单（以代码实现为准）

> 目的：用“实现视角”快速解释项目是怎么拼起来的，并给出一份可执行的优先级 TODO（带完成勾选）。
>
> 最终架构设计以 `doc/design/Architecture.md` 为准；本文档仅描述“当前实现视角”，并尽量通过引用保持与权威设计一致。
>
> 状态来源：代码目录结构 + `openspec list` / `openspec/changes/*/tasks.md`（最后更新：2026-01-22）。

## 1. 架构现状（实现视角）

### 1.1 分层与目录职责

- `dare_framework/core/`：当前实现中的 Kernel contracts + 数据结构（设计基线：`doc/design/Architecture.md`；接口清单：`doc/design/Interfaces.md`）
  - Kernel 默认实现按 domain package 归档（例如 `core/event/local_event_log.py`、`core/execution_control/file_execution_control.py`、`core/tool/tool_manager.py`）
- `dare_framework/contracts/`：共享 contracts/types（tools/model/evidence/risk/run_context 等；供 components/protocols/builder 复用）
- `dare_framework/protocols/`：Layer 1 Protocol Adapters（如 MCP），负责能力发现/调用的协议适配
- `dare_framework/components/`：Layer 2 Pluggable Components（planner/validator/remediator/providers/tools 等默认实现）
- `dare_framework/components/plugin_system/`：entrypoints 插件机制（组件发现 + manager 接口/实现；不进入 Kernel）
- `dare_framework/builder.py`：Layer 3 Developer API（`AgentBuilder` + `Agent` wrapper），用于显式组装 Kernel 与组件
- `examples/`：可运行示例（例如 stdin/stdout chat）
- `tests/`：单元/集成测试

### 1.2 关键运行链路（从 build 到 RunResult）

1. `AgentBuilder.build()` 组装 Kernel 默认实现 + Layer 2 组件 + providers，返回 `Agent`（见 `dare_framework/builder.py`）
2. `Agent.run(task, deps)` 将 `deps` 绑定到运行态上下文（不进入 Task 以保持可序列化审计），随后进入编排执行（当前实现：`IRunLoop.run(Task)`）
3. 编排驱动五层循环骨架（Session/Milestone/Plan/Execute/Tool）（当前实现：`IRunLoop` → `ILoopOrchestrator`；设计文档：编排归入 `agent` 域，详见 `doc/design/Architecture.md`）
4. **Plan Loop（信息隔离）**：`IContextManager.assemble(PLAN)` → `IPlanner.plan()` → `IValidator.validate_plan()`；失败会在预算内重试或交给 `IRemediator`（可先 no-op）
5. **Execute/Tool Loop（副作用边界）**：所有外部动作都经由 `IToolGateway.invoke(capability_id, params, envelope)`；`ToolLoopRequest + Envelope + DonePredicate` 决定“何时完成/何时重试”
6. **控制面与外化**：预算由 `IResourceManager` 约束，暂停/恢复/Checkpoint 由 `IExecutionControl` 统一处理，证据与决策写入 `IEventLog`（WORM，可重放）

### 1.3 状态、审计与可观测性

- 事件日志（WORM）：`LocalEventLog` 追加写入 `.dare/<agent_name>/event_log.jsonl`，维护 `prev_hash`/`event_hash` hash-chain，支持最小 replay/query
- Checkpoint：`FileExecutionControl` 写入 `.dare/<agent_name>/checkpoints/*.json`（pause/HITL/显式 checkpoint）
- 资源预算：`InMemoryResourceManager` 提供粗粒度预算（tool calls/time/token/cost 可逐步细化）
- 扩展点：`DefaultExtensionPoint` 作为 best-effort hooks registry（便于后续接入 tracing/telemetry/policy taps）

### 1.4 配置与插件扩展点

- builder 采取“显式组装优先”：通过 `AgentBuilder.with_*()` 注入 planner/validator/remediator/tools/protocol adapters/model 等依赖，避免隐式全局插件带来的不确定性。
- entrypoints 插件机制位于 `dare_framework/components/plugin_system/`：builder 可选择性接入 managers 做确定性的发现/过滤/排序（无需 Kernel 依赖 `importlib.metadata`）。

## 2. 优先级清单（Checklist）

> 优先级默认按“阻塞程度/对可运行性影响”排序；如果你们有明确里程碑，可直接调整本节顺序。

### P0（必须）：保证核心链路可跑通、可验证

- [x] Kernel 五层循环跑通（Session/Milestone/Plan/Execute/Tool）
- [x] EventLog/预算/Checkpoint 接口打通，核心流程形成证据闭环
- [x] 示例与测试可回归（`pytest`）

### P1（应该）：让示例链路可复现、可回归

- [ ] HITL 语义：将“pause 后立即 resume”的 stub 替换为可外部驱动的等待/恢复（`IRunLoop.state = WAITING_HUMAN`）
- [ ] 协议适配：MCP/其它 adapters 在 invoke 时接入 RuntimeStateView（替换当前 stub RunContext）
- [ ] Context 工程：补齐 `IContextManager` 的 no-op 占位方法（compress/retrieve/ensure_index/route）的事件记录与预算归因

### 已完成（来源：`openspec list`）

- [x] `add-dare-framework-foundation`
- [x] `refactor-layered-structure`
- [x] `refactor-component-managers`
- [x] `refine-component-manager-config`
- [x] `add-component-manager-entrypoints`

## 3. 相关“权威设计”文档入口（阅读顺序）

1. `openspec/project.md`（项目上下文/约束/架构总览）
2. `doc/design/Architecture.md`（最终架构设计：权威）
3. `doc/design/Interfaces.md`（权威接口清单）
4. `doc/design/DARE_alignment.md`（对齐清单：claims → 证据/实现）
5. `doc/guides/Development_Constraints.md`（开发约束清单）
6. `doc/design/archive/Architecture_Final_Review_v2.1.md` / `doc/design/archive/Architecture_Final_Review_v1.3.md`（历史参考）
