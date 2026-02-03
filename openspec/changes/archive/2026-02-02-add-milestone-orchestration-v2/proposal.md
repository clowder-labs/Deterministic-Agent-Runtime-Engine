# Change: 增强 Milestone 编排能力（自动拆分、隔离、证据闭环、步骤驱动执行）

## Why

当前 DARE Framework 的 Milestone 机制已有基础骨架（重试、验证、补救），但存在四个关键能力缺口：

1. **无 LLM 自动拆分能力**：复杂任务只能开发者手动预定义 milestones，缺少 `IPlanner.decompose` 方法
2. **Plan Attempt 未隔离**：已有 spec 要求但未实现，失败的 plan 消息仍污染 STM
3. **证据闭环不强制**：`verify_milestone` 无法强制检查 `success_criteria`，缺少结构化证据收集
4. **Plan steps 未驱动执行**：ValidatedPlan.steps 仅作参考，Execute Loop 仍由模型自由驱动

这些能力是框架达成"外部可验证完成"和"可审计执行"设计目标的必要条件。

## What Changes

### 1. Milestone 自动拆分（NEW）
- 在 `IPlanner` 接口添加 `decompose(task, ctx) -> list[Milestone]` 方法
- 新增 `DecompositionResult` 类型用于携带拆分结果与元数据
- Session Loop 在 milestones 为空时调用 decompose 自动生成

### 2. Plan Attempt 隔离（ENHANCED）
- 新增 `IPlanAttemptSandbox` 接口支持 STM snapshot/rollback
- Execute Loop 在 plan 失败时 rollback 到 attempt 开始前状态
- 只有成功的 plan 结果和反思文本可持久化到外层

### 3. 强制证据闭环（NEW）
- 新增 `Evidence` 类型与 `IEvidenceCollector` 接口
- `VerifyResult` 扩展 `evidence_required` / `evidence_collected` 字段
- Validator 可强制检查 `success_criteria` 与收集的证据匹配

### 4. Plan Steps 驱动执行（ENHANCED）
- 新增 `IStepExecutor` 接口支持按 step 顺序执行
- 修改 Execute Loop 从"模型自由驱动"改为"步骤约束驱动"
- 每个 step 执行结果作为下一步的输入上下文

## Impact

### Affected Specs
- **plan-module**: 添加 decompose 接口、Evidence 类型
- **core-runtime**: 增强 Plan Attempt Isolation、添加 Step-Driven Execution

### Affected Code
- `dare_framework/plan/interfaces.py` - 新增 decompose、IStepExecutor
- `dare_framework/plan/types.py` - 新增 Evidence、DecompositionResult
- `dare_framework/agent/_internal/five_layer.py` - 修改 Session/Milestone/Execute Loop
- `dare_framework/agent/_internal/orchestration.py` - 新增 sandbox 支持

### Breaking Changes
- **BREAKING**: `IPlanner` 接口新增 `decompose` 方法（需实现或继承 default）
- 非破坏性：现有 `Task.milestones` 预定义方式继续支持
