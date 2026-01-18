# 框架对比：AgentScope（2026-01 更新）

本页为框架对比的最新整理，重点聚焦 AgentScope，并补充 DARE 的必要性与可复用理念。资料来源见文末（更新：2026-01-15）。

## 结论速览

- AgentScope 已从“多 agent 框架”演进为“平台化 AOP 工具箱”，覆盖模型、工具、记忆、计划、评估、观测、运行时与 Studio 的完整链路。
- 但 AgentScope 的主目标仍是“开发效率与多 agent 协作”，对“确定性、可审计、强政策约束的运行时”关注较少。
- DARE 的必要性在于：提供确定性执行、信任边界与审计证据链，让 AI 任务在合规/安全/长期运行场景中可控、可复现、可证明。

## AgentScope 最新定位（v1 公开信息）

- 核心理念：Agent-Oriented Programming（AOP）+ developer-centric transparency。
- 模块覆盖：model、tool、agent、memory、session/state、plan、evaluation、tracing、RAG、MCP、A2A。
- 运行时与可视化：AgentScope Runtime（工具沙盒、Docker/K8s、VNC 视觉沙盒）与 AgentScope Studio。
- 关键能力：异步/并行工具调用、流式工具输出、实时介入与自定义中断、工具分组与 Meta Tool、长期记忆与压缩、OpenTelemetry 追踪。

## 更新版框架对比（概览）

| 维度 | LangChain/LangGraph | AgentScope | DSPy | PydanticAI |
|------|---------------------|-----------|------|------------|
| 核心定位 | 生态编排/工作流 | AOP 多 agent 平台 | 编程化 prompt/程序优化 | 类型安全 LLM SDK |
| 核心优势 | 集成广、LangGraph 有状态流程 | 模块齐全、透明、多 agent、Studio/Runtime | eval 驱动的自动优化 | 结构化输出、依赖注入、轻量 |
| 多 agent | LangGraph 支持 | 原生优先 | 非核心 | 有限 |
| 运行时/部署 | LangGraph Platform | agentscope-runtime | 非核心 | 非核心 |
| 观测/调试 | LangSmith | OpenTelemetry | 需外接 | Logfire |
| 主要不足 | 抽象复杂/迁移成本 | 确定性与审计非重点 | 生产链路短 | 多 agent/运行时能力弱 |

## DARE vs AgentScope（重点对比）

| 维度 | AgentScope | DARE |
|------|-----------|------|
| 目标 | 多 agent 开发效率与透明度 | 确定性运行时 + 审计 + 政策约束 |
| 执行模型 | AOP + 模块化编排 | 状态机化 runtime + 五层循环 |
| 计划/执行隔离 | 未强调隔离 | Plan Loop / Execute Loop 强隔离 |
| 信任边界 | 以透明为主 | TrustBoundary + Registry 强约束 |
| 审计/证据 | tracing/logging | IEventLog + Hash Chain |
| 策略与权限 | 交由业务或工具实现 | IPolicyEngine（policy-as-code） |
| 状态管理 | session/state + memory | ICheckpoint + EventLog |
| 互操作 | MCP + A2A | MCP 适配 + Skill Registry（A2A 可借鉴） |
| 可视化/运行时 | Studio + Runtime | 以运行时可靠性为核心，可对接可视化 |

## 为什么 DARE 仍然必要

- **确定性与可复现**：通过状态机化 runtime、Plan/Execute 隔离与持久化事件链，让执行路径可重放、可验证。
- **信任边界与安全**：把 LLM 输出视为不可信输入，只有经过 Registry 与策略校验的数据才能进入可信状态。
- **审计证据链**：IEventLog + Hash Chain 形成可追溯、可防篡改的执行证据，满足合规与风控需求。
- **强策略与人审**：IPolicyEngine 与 HITL Approve 为高风险工具调用提供硬约束与责任链。
- **长期运行可靠性**：ICheckpoint 明确保存与恢复边界，降低长任务崩溃恢复的不可控性。

## 可复用的先进理念

**来自 AgentScope**

- 模块化 + 透明原则：减少“黑箱魔法”，提升可调试性和可维护性。
- 实时介入与自定义中断：适配人机协作与运行时纠偏（DARE 可复用现有中断意图提取）。
- 工具分组与 Meta Tool：让工具治理更细粒度。
- Plan / Evaluation 模块：为规划与效果评估提供标准化能力。
- MCP/A2A 互操作：提升跨框架与跨组织的 agent 协作。
- Runtime 沙盒与 Studio：提升生产部署与可视化调试能力。
- 记忆压缩 + 数据库记忆：降低上下文成本，增强长期任务稳定性。

**来自其他框架**

- LangGraph 的 checkpoint/time-travel 思路：与 DARE 的 ICheckpoint + EventLog 形成互补。
- DSPy 的 eval 驱动优化：用于自动校准计划质量与工具选择策略。
- PydanticAI 的类型安全与依赖注入：保持结构化输出与可靠接口。

## 资料来源

- AgentScope README: https://github.com/agentscope-ai/agentscope
- AgentScope Docs: https://doc.agentscope.io/zh_CN/
- AgentScope Roadmap: https://github.com/agentscope-ai/agentscope/blob/main/docs/roadmap.md
- AgentScope Runtime: https://github.com/agentscope-ai/agentscope-runtime
- AgentScope Studio: https://github.com/agentscope-ai/agentscope-studio
