# DARE 对齐校验（Evidence ↔ Docs）

用途：帮助 reviewer 快速确认权威文档结论均可追溯到 evidence claims。

输入：
- `doc/design/Architecture.md`
- `doc/design/Interfaces.md`
- `doc/design/DARE_evidence.yaml`

---

## 1) Claim → 文档落点（快速映射）

| Claim | 摘要 | 架构文档落点 | 接口文档落点 |
|---|---|---|---|
| C-EXEC-001 | IAgent.run 为最小运行面；编排在 agent（多实现）；不把 run-loop 当 Kernel 稳定接口 | Architecture.md#2.2 分层说明（关键决策）；Architecture.md#4.7 多编排支持（agent 域） | Interfaces.md#1 |
| C-ARCH-001 | 五层循环是 DARE 的 canonical 编排骨架 | Architecture.md#3.2 五层循环定义（结构骨架） | Interfaces.md#4 |
| C-ARCH-002 | 风险/审批等字段必须来自可信 registry（非 LLM 自报） | Architecture.md#1.3 不变量（必须长期成立）；Architecture.md#4.1 统一能力模型（Capability）与系统调用边界；Architecture.md#4.2 安全边界（Trust / Policy / Sandbox） | Interfaces.md#3, #6 |
| C-CTX-001 | Context-centric：messages request-time 组装 | Architecture.md#4.4 上下文工程（Context Engineering） | Interfaces.md#2, #10 |
| C-CTX-002 | Context 持有 STM/LTM/Knowledge 引用 + Budget；assemble 按需组装 messages/tools（结构化 tool defs） | Architecture.md#4.4 上下文工程（Context Engineering） | Interfaces.md#2 |
| C-TOOL-001 | IToolGateway.invoke 是副作用单一边界 | Architecture.md#1.3 不变量（必须长期成立）；Architecture.md#4.1 统一能力模型（Capability）与系统调用边界 | Interfaces.md#3 |
| C-PROTOCOL-001 | protocol adapter 翻译成 canonical CapabilityDescriptor | Architecture.md#2.1 架构总览图；Architecture.md#4.1 统一能力模型（Capability）与系统调用边界 | Interfaces.md#3 |
| C-MODEL-001 | ModelInput(messages + trusted tools + metadata) 标准化输入面 | Architecture.md#4.4 上下文工程（Context Engineering）；Architecture.md#5. 关键组件能力设计（按 domain 摘要） | Interfaces.md#5 |
| C-PLAN-001 | Plan Attempt Isolation + Proposed/Validated 分离 | Architecture.md#3.3 核心约束：Plan Attempt Isolation（失败计划隔离） | Interfaces.md#4 |
| C-PLAN-TOOL-001 | Plan Tool 触发停止执行并回外层 re-plan | Architecture.md#3.4 核心约束：Plan Tool（控制类工具） | Interfaces.md#11 |
| C-HITL-001 | HITL：pause/wait_for_human/resume + 审计事件链 | Architecture.md#4.3 HITL（人在回路） | Interfaces.md#3 |
| C-EVENT-001 | EventLog：WORM + query/replay（可选 hash-chain） | Architecture.md#4.5 审计与可重放（EventLog / Checkpoint / Replay） | Interfaces.md#7 |
| C-HOOK-001 | ExtensionPoint：hooks 默认 best-effort | Architecture.md#4.8 Hooks 扩展点（ExtensionPoint） | Interfaces.md#8 |
| C-PLUG-001 | entrypoints 属于 Layer 3 managers（确定性） | Architecture.md#2.2 分层说明（关键决策）；Architecture.md#4.6 确定性装配与插件系统（Managers） | Interfaces.md#9 |
| C-DOMAIN-001 | domain 文件约定：types/kernel/interfaces/_internal | Architecture.md#2.3 分域（DDD）与文件约定（硬规则） | Interfaces.md#0 |
| C-PKG-001 | 目标包名 dare_framework；后续收敛并清理多版本目录 | Architecture.md#1.1 定位；Architecture.md#6. 文档驱动收敛与清理计划（摘要） | Interfaces.md#0 |

---

## 2) 章节覆盖检查

### Architecture.md
- #1：C-PKG-001 / C-ARCH-002 / C-TOOL-001
- #2：C-EXEC-001 / C-PROTOCOL-001 / C-PLUG-001 / C-DOMAIN-001
- #3：C-ARCH-001 / C-PLAN-001 / C-PLAN-TOOL-001
- #4：C-ARCH-002 / C-CTX-001 / C-CTX-002 / C-MODEL-001 / C-HITL-001 / C-EVENT-001 / C-HOOK-001 / C-TOOL-001 / C-PROTOCOL-001 / C-PLUG-001
- #5：C-MODEL-001（组件视角的落点补充）
- #6：C-PKG-001

### Interfaces.md
- #0：C-DOMAIN-001
- #1：C-EXEC-001
- #2：C-CTX-001 / C-CTX-002
- #3：C-TOOL-001 / C-HITL-001 / C-PROTOCOL-001 / C-ARCH-002
- #4：C-PLAN-001
- #5：C-MODEL-001
- #6：C-ARCH-002
- #7：C-EVENT-001
- #8：C-HOOK-001
- #9：C-PLUG-001
- #10：C-CTX-001
- #11：C-PLAN-TOOL-001
