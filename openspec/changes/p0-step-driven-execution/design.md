## Context

`DareAgent` 已具备 `execution_mode`、`IStepExecutor`、`ValidatedStep` 等基础结构，但当前主执行路径未消费这些能力。计划环与执行环之间缺乏硬连接，使 `ValidatedPlan` 不能稳定约束实际工具调用顺序，也削弱了后续验证与审计信号。

## Goals / Non-Goals

**Goals:**
- 让 `execution_mode` 成为真实运行时开关。
- 在 `step_driven` 模式下按 step 顺序执行并收集 evidence。
- 定义 step 失败行为（中断/继续策略）并输出可复验结果。
- 保持 `model_driven` 路径兼容，避免现有行为大面积回归。

**Non-Goals:**
- 本次不实现 DAG 并发 step 调度，仅支持顺序执行。
- 本次不重写 planner 产出格式，只做最小转换与执行接线。
- 本次不扩展复杂依赖表达式（如跨 step 条件分支语言）。

## Decisions

### Decision 1: 执行模式双轨并存
- `model_driven` 继续沿用模型 tool-calls 驱动。
- `step_driven` 仅消费 `ValidatedPlan.steps`，不再每轮向模型请求工具选择。
- 理由：先保证可控执行路径，再逐步扩展高级编排。

### Decision 2: 复用现有 `IStepExecutor`
- 直接复用 `DefaultStepExecutor`，由 agent 注入执行。
- 每步产出 `StepResult`，并将 evidence 聚合到 execute result。
- 理由：避免重复实现，快速让现有抽象落地。

### Decision 3: 失败策略默认 fail-fast
- 任一步 `success=False` 默认终止后续 steps。
- 输出包含已完成步骤、失败步骤、错误列表，供 remediator/validator 使用。
- 理由：P0 先保证行为可预测，后续再考虑容错重试策略。

### Decision 4: 统一 verify 输入结构
- 无论执行模式，verify 阶段都接收标准化 `RunResult` 与可选 plan。
- `step_driven` 模式额外传递 step 汇总（成功数、失败数、evidence）。
- 理由：保证 validator 兼容并增强可解释性。

## Risks / Trade-offs

- [Risk] 部分任务依赖模型在线推理决策，切到 step 模式可能能力下降。  
  → Mitigation: 默认保持 `model_driven`，按场景显式启用 `step_driven`。
- [Risk] planner step 质量不足会直接影响执行成功率。  
  → Mitigation: 先在 validator 中加强 step 完整性校验并提供清晰报错。
- [Risk] 双模式并存增加维护复杂度。  
  → Mitigation: 共享 execute result 与 verify 接口，避免分叉过深。

## Migration Plan

1. 在 agent 中实现 execution mode 分支，先接通 `step_driven` 基础路径。
2. 注入默认 step executor，并完成 step 结果聚合格式。
3. 增加无 validator 场景下 `ProposedStep -> ValidatedStep` 最小转换。
4. 更新 verify 入口以接收 step 汇总并验证兼容性。
5. 通过单测与集成测试验证双模式不互相回归。

Rollback:
- 配置回退至 `model_driven` 默认路径并禁用 `step_driven` 分支。

## Open Questions

- `step_driven` 是否需要按 step 级别支持重试次数配置？
- `_previous_output` 上下文注入是否需要标准命名与 schema 限制？
- 长任务下是否要把 step 进度实时透传到 transport（用于 UI 展示）？
