## 1. Execution Mode Activation

- [ ] 1.1 在 `DareAgent` 中启用 `execution_mode` 分支选择逻辑。
- [ ] 1.2 保持 `model_driven` 现有行为并补充兼容性断言。
- [ ] 1.3 新增 `step_driven` 路径入口并接入 execute loop。

## 2. Step Executor Integration

- [ ] 2.1 将 `IStepExecutor` 注入到 `DareAgent` 默认构建路径。
- [ ] 2.2 在 `step_driven` 模式按 `ValidatedPlan.steps` 顺序执行。
- [ ] 2.3 聚合 `StepResult` 与 `Evidence` 到统一 execute result 结构。
- [ ] 2.4 实现 step 失败 fail-fast 与错误传播。

## 3. Plan-to-Step Bridge

- [ ] 3.1 补齐无 validator 场景下的最小 step 转换逻辑。
- [ ] 3.2 增加 step 合法性校验（capability、params、envelope 基础检查）。
- [ ] 3.3 在 verify 阶段透传 plan 与 step 汇总信息。

## 4. Tests and Regression

- [ ] 4.1 新增单测验证 step 顺序执行与失败中断语义。
- [ ] 4.2 新增单测验证 evidence 聚合格式与字段完整性。
- [ ] 4.3 新增集成测试覆盖 `step_driven` 完整链路（plan->execute->verify）。
- [ ] 4.4 回归测试确保 `model_driven` 路径无行为退化。
