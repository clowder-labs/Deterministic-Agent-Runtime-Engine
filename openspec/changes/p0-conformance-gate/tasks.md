## 1. Define Gate Scope

- [ ] 1.1 定义 `p0-gate` 覆盖的三类不变量与验收阈值。
- [ ] 1.2 明确每类不变量对应的测试文件与责任模块。
- [ ] 1.3 定义标准失败标签与 CI summary 输出格式。

## 2. Build P0 Test Suite

- [ ] 2.1 新增集成测试覆盖安全门控主链路（allow/deny/approve_required）。
- [ ] 2.2 新增集成测试覆盖 `step_driven` 执行闭环。
- [ ] 2.3 新增集成测试覆盖默认 event log hash-chain/replay。
- [ ] 2.4 增加关键单测确保契约字段与错误码稳定。

## 3. CI Integration

- [ ] 3.1 在 CI workflow 增加 `p0-gate` job 与命令入口。
- [ ] 3.2 将 `p0-gate` 配置为主分支 required check。
- [ ] 3.3 输出标准化门禁报告（通过率、失败类型、建议排查点）。

## 4. Operationalization

- [ ] 4.1 更新开发文档，说明本地运行与故障排查流程。
- [ ] 4.2 在发布流程增加 `p0-gate` 结果归档步骤。
- [ ] 4.3 制定 flaky 用例处理规则与时限。
