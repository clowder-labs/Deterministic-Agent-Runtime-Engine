## 1. 实现
- [ ] 1.1 对齐 plan 数据模型（Proposed/Validated、Envelope/ToolLoopRequest、可信 metadata 承载）并更新公开导出。
- [ ] 1.2 补齐 plan 策略接口语义（IPlanner/IValidator/IRemediator 及 manager）与必要注释。
- [ ] 1.3 在五层循环中落实 Plan Attempt Isolation 与 Plan Tool 回退行为（仅持久化 attempt 元信息与 reflection）。
- [ ] 1.4 Validator 基于可信 registry 派生风险/审批元数据并写入 ValidatedStep。
- [ ] 1.5 增补测试：计划分层、无效计划不外泄、Plan Tool 触发回到 Plan Loop。
- [ ] 1.6 验证：运行相关 pytest 目标，并执行 `openspec validate update-plan-module-v4 --strict`。
