# DARE Framework 文档导航

> 本文档提供清晰的阅读顺序和文档分类（以 `/docs/` 为范围）。

---

## 📖 推荐阅读顺序

### 快速上手（最终架构设计以权威文档为准）

```text
1. 项目概览
   └── /openspec/project.md (项目上下文、技术栈、架构概览)

2. 核心架构（权威设计）
   └── design/Architecture.md

3. 接口设计（权威设计）
   └── design/Interfaces.md

4. 设计对齐与证据（可选但推荐）
   ├── design/DARE_alignment.md
   └── design/DARE_evidence.yaml

5. 代码实现（以权威设计文档为准）
   └── dare_framework/（当前实现；若与权威设计不一致，需先修订设计并执行 gap 分析）

6. 示例实现
   ├── /examples/04-dare-coding-agent/ (五层循环示例 Agent)
   ├── /examples/06-dare-coding-agent-mcp/ (Config 驱动 MCP + 动态重载示例)
   ├── /examples/07-tool-approval-memory/ (工具审批记忆与自动放行示例)
   └── /examples/08-hook-governance/ (Hook 治理：patch + block 示例)

7. CLI 使用与配置
   ├── /client/README.md (命令入口、`.dare/config.json`、LLM 配置说明)
   ├── /.dare/config.json.example (OpenAI 最小配置)
   ├── /.dare/config.openrouter.example.json (OpenRouter 最小配置)
   └── /.dare/config.advanced.example.json (进阶配置示例)

8. 开发规范
   ├── /CONTRIBUTING_AI.md (AI Agent 协作规范)
   ├── guides/Development_Constraints.md (开发约束清单)
   ├── guides/Documentation_First_Development_SOP.md (文档先行 SOP，Bug/Feature/Refactor 必走)
   ├── guides/Evidence_Truth_Implementation_Strategy.md (Evidence Truth 固化策略与 CI 落地计划)
   ├── guides/P0_Gate_Runbook.md (P0 gate 本地运行、发布归档、flaky 处理操作手册)
   ├── governance/Documentation_Management_Model.md (文档目录分层、生命周期、OpenSpec/TODO 双模式协作)
   ├── features/README.md (特性聚合文档规范与归档规则)
   └── design/Design_Doc_Minimum_Standard.md (设计文档最小完备标准)
```

### 历史参考（v1.3）

```text
1. v1.3 架构终稿（历史参考）
   └── design/archive/Architecture_Final_Review_v1.3.md

2. v1.1 接口层设计（历史参考）
   └── design/archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md
```

---

## 📂 文档分类

### 1️⃣ 核心设计文档（最终架构设计）

| 文档 | 作用 | 状态 |
|---|---|---|
| `design/Architecture.md` | **架构设计**<br/>不变量、分层/分域、核心流程与关键约束、清理计划 | ⭐ 最终架构设计 |
| `design/Interfaces.md` | **接口设计**<br/>按 domain 的接口位与数据结构（权威签名/类型） | ⭐ 权威接口 |
| `design/DARE_Formal_Design.md` | **正式设计文档**<br/>面向整体架构与核心流程的最终设计 | ⭐ 最终设计 |
| `design/modules/README.md` | **模块级设计索引**<br/>按 Agent/模块分区的详细设计入口（含 Agent 示例） | ✅ 详细设计 |
| `design/Design_Doc_Minimum_Standard.md` | **设计文档最小完备标准**<br/>约束每份设计文档必须覆盖架构/流程/结构/接口/异常 | ✅ 治理标准 |
| `design/DARE_alignment.md` | **对齐清单**<br/>当前架构/接口的 claim → 证据/实现映射 | ✅ 对齐与追溯 |
| `design/DARE_evidence.yaml` | **证据索引**<br/>claims + sources + anchors（用于文档一致性与回归） | ✅ 对齐与追溯 |

### 2️⃣ 代码与工程入口（实现必须对齐设计）

| 文档/目录 | 作用 | 状态 |
|---|---|---|
| `dare_framework/` | 框架实现主目录（目标收敛到单一架构；详见权威设计） | ✅ 实现入口 |
| `client/README.md` | DARE Client CLI 用法与配置入口，含 `.dare/config.json` 和 LLM 配置说明 | ✅ CLI 入口 |
| `.dare/config.json.example` | OpenAI 最小配置示例，可作为 workspace `.dare/config.json` 起点 | ✅ 配置示例 |
| `.dare/config.openrouter.example.json` | OpenRouter 最小配置示例 | ✅ 配置示例 |
| `.dare/config.advanced.example.json` | 含 `endpoint/proxy/max_tokens` 的进阶配置示例 | ✅ 配置示例 |
| `Project_Architecture_and_Priorities.md` | 以“实现视角”梳理现状与优先级（阅读入口指向权威设计） | ✅ 实现视角 |
| `todos/README.md` | TODO 目录维护规则与生命周期说明 | ✅ 全局规划 |
| `todos/project_overall_todos.md` | 项目总体 TODO 清单（跨模块路线图） | ✅ 全局规划 |
| `todos/templates/change_execution_todo_template.md` | 活跃 change 的 execution board 模板（大包认领，小 task 验收） | ✅ 协作模板 |
| `plans/2026-02-28-spec-driven-collaboration-granularity-design.md` | spec-driven 协作粒度设计说明 | ✅ 协作设计 |

### 3️⃣ 附录与工程实践

| 文档 | 作用 |
|---|---|
| `appendix/Appendix_Industrial_Security_and_Auditing.md` | 工业级安全与审计附录：WORM、Merkle 批次密封、审计复验 |
| `guides/Engineering_Practice_Guide_Sandbox_and_WORM.md` | 工程实践指南：沙箱执行隔离（seccomp/网络/镜像）、WORM 落地与核查 |
| `guides/Development_Constraints.md` | 开发约束：架构不破坏、测试必备、日志/命名/复用/信任边界等硬性要求 |
| `guides/Documentation_First_Development_SOP.md` | 文档先行 SOP：先设计文档、再 gap 分析、再 TODO、再 OpenSpec 修复、再归档 |
| `guides/Evidence_Truth_Implementation_Strategy.md` | Evidence Truth 固化策略：证据结构、审计要求、CI 分阶段落地 |
| `guides/P0_Gate_Runbook.md` | P0 gate 操作手册：本地执行、失败分诊、发布归档、flaky 策略 |
| `governance/Documentation_Management_Model.md` | 文档管理模型：目录分层、文档类型规则、生命周期依赖、OpenSpec/无 OpenSpec 协作 |
| `features/README.md` | 特性聚合文档规范：单一状态源、证据回写与归档迁移 |
| `guides/Team_Agent_Collab_Playbook.md` | 团队并行开发协作手册，含 spec-driven 认领粒度与 execution board 规则 |
| `guides/Tool_Approval_Memory.md` | 工具审批记忆使用指南：pending/grant/deny/revoke、scope/matcher、持久化与接线方式 |
| `features/templates/feature_aggregation_template.md` | 特性聚合模板：用于新建 `docs/features/<change-id>.md` |
| `features/archive/README.md` | 特性聚合归档索引：记录已归档 change 的入口与迁移规则 |

---

## 🗄️ 归档材料（历史参考）

这些文档用于追溯设计演进过程，不作为“当前标准”。归档文件位于 `design/archive/`。

<details>
<summary>点击展开归档列表</summary>

### 历史设计终稿与草案（已被当前权威设计取代）

| 文档（位于 `design/archive/`） | 版本/类型 | 备注 |
|---|---|---|
| `Architecture_Final_Review_v1.3.md` | v1.3（终稿） | 历史参考 |
| `Architecture_Final_Review_v2.0.md` | v2.0（终稿评审） | 历史参考 |
| `Architecture_Final_Review_v2.1.md` | v2.1（终稿评审） | 历史参考 |
| `Architecture_v2.0_Proposal.md` | v2.0（草案） | 历史参考 |
| `Interface_Layer_Design_v1.1_MCP_and_Builtin.md` | v1.1（接口层设计） | 历史参考 |

### v3.x 对比与演进材料（历史参考）

| 文档（位于 `design/archive/`） | 类型 | 备注 |
|---|---|---|
| `ARCHITECTURE_COMPARISON.md` | v1 vs v2 vs v3 愿景 | 包含历史演进记录（历史资料） |

### 设计版本归档（已被 v1.3 取代）

> 说明：这里的 `Industrial_Agent_Framework_*` 属于更早期的工业框架草案（历史资料），与后续架构草案不是同一条版本线；请以文件名与目录为准。

| 文档（位于 `design/archive/`） | 版本/类型 | 备注 |
|---|---|---|
| `Industrial_Agent_Framework_Design_v2.md` | v2.0（早期草案） | 历史参考 |
| `Industrial_Agent_Framework_v2.1_Supplement.md` | v2.1 | 历史参考 |
| `Industrial_Agent_Framework_v2.2_Supplement.md` | v2.2 | 历史参考 |
| `Industrial_Agent_Framework_v2.3_Supplement.md` | v2.3 | 历史参考 |
| `Industrial_Agent_Framework_v2.4_Verifiable_Closures.md` | v2.4 | 历史参考 |
| `Agent_Framework_Skeleton_v1.md` | v1.0 | 历史参考 |
| `Interface_Layer_Design_v1.md` | v1.0 | 被 v1.1 取代 |
| `Architecture_Review_and_Gaps.md` | review notes | 被 v1.3 吸收 |
| `Architecture_Final_Review_v1.md` | v1.0 | 被 v1.3 取代 |
| `Architecture_Final_Review_v1.1.md` | v1.1 | 被 v1.3 取代 |
| `Architecture_Final_Review_v1.2.md` | v1.2 | 被 v1.3 取代 |
| `Architecture_Final_Review_v1_Addendum.md` | addendum | 历史参考 |
| `Agent_Framework_Loop_Model_v2.2_Final.md` | v2.2 | 历史参考 |
| `Agent_Framework_Image_Prompts.md` | prompts | 历史参考 |

### v2.0 草案产出过程（v1.3 → v2.0）

| 文档（位于 `design/archive/`） | 类型 | 备注 |
|---|---|---|
| `Architecture_v2.0_Claude_Feedback_Analysis.md` | 决策依据 | Claude 反馈综合分析与 v2.0 决策依据 |
| `Architecture_v1.3_Claude_Feedback_1.md` | 原始反馈 | Claude 对 v1.3 的反馈（1） |
| `Architecture_v1.3_Claude_Feedback_2.md` | 原始反馈 | Claude 对 v1.3 的反馈（2） |

### 对比/研究资料（历史参考）

| 文档（位于 `design/archive/`） | 类型 | 备注 |
|---|---|---|
| `Framework_Comparison_PydanticAI.md` | 对比分析 | PydanticAI 对比（历史资料） |
| `Framework_Comparison_AgentScope.md` | 对比分析 | AgentScope 对比（历史资料） |
| `anthropic-engineering.md` | 参考资料 | Anthropic 工程最佳实践参考（历史资料） |
| `Gemini_Generated_Image_im2qiuim2qiuim2q.png` | 图片 | 生成的架构示意图（未必与当前权威设计对齐） |

</details>

---

## 🎯 按角色推荐阅读

### 架构师 / Tech Lead

```text
1. design/Architecture.md（最终架构设计）
2. design/Interfaces.md（权威接口）
3. design/DARE_alignment.md（对齐与证据入口）
4. /openspec/project.md（项目约束与变更流程）
5. guides/Development_Constraints.md
6. dare_framework/（当前实现入口）
```

### 后端工程师（实现框架）

```text
1. design/Architecture.md
2. design/Interfaces.md
3. dare_framework/
4. /openspec/project.md
5. guides/Development_Constraints.md
```

### Agent 开发者（使用框架）

```text
1. /examples/04-dare-coding-agent/README.md
2. /examples/07-tool-approval-memory/README.md
3. guides/Tool_Approval_Memory.md
4. design/Architecture.md（理解框架目标形态与边界）
5. dare_framework/builder.py（组装 API）
```

---

## 📋 文档维护规则

### 创建新文档时

1. **主设计文档**：保持无版本命名，更新时同步更新本 README
2. **补充/对比文档**：使用清晰主题命名（如 `Framework_Comparison_*.md`）
3. **过程材料/过时文档**：移动到 `design/archive/` 目录

### 更新文档时

1. 如果是**重大修改**：更新主文档，并将被替代版本归档到 `design/archive/`
2. 如果是**小修改**：直接更新现有文档
3. 更新本 README 的“最后更新日期”

### 归档标准

文档满足以下任一条件时应归档：
- 被更新版本完全取代
- 不再是“当前标准”
- 仅作历史参考或过程记录

---

## 🔄 文档演进历史

```text
Phase 1: 初始设计（Industrial Agent Framework 早期草案，已归档）
├── archive/Industrial_Agent_Framework_Design_v2.md
└── archive/v2.1 ~ v2.4 Supplements

Phase 2: 接口设计（早期版本，已归档）
├── archive/Interface_Layer_Design_v1.md
└── archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md

Phase 3: 框架对比与融合
├── archive/Framework_Comparison_PydanticAI.md
├── archive/Framework_Comparison_AgentScope.md
└── archive/anthropic-engineering.md

Phase 4: 架构终稿（历史参考）
└── archive/Architecture_Final_Review_v1.3.md

Phase 5: 架构内核化（历史参考）
├── archive/Architecture_v2.0_Proposal.md
├── archive/Architecture_Final_Review_v2.0.md
└── archive/Architecture_Final_Review_v2.1.md

Phase 6: 架构设计（当前权威）
├── Architecture.md
└── Interfaces.md
```

---

## ❓ 常见问题

### Q: 现在应该以哪个文档为准？

**A:** 最终架构设计以权威文档为准：
- **架构**：`design/Architecture.md`
- **接口**：`design/Interfaces.md`
- **对齐/证据**：`design/DARE_alignment.md` + `design/DARE_evidence.yaml`

> 说明：实现必须对齐权威设计；若发现差异，请先更新设计文档并执行 gap 分析，再推进代码修复与迁移计划。

### Q: 为什么会看到两个 “v2.0”？

**A:** 这是历史原因导致的命名重叠：
- `design/archive/Industrial_Agent_Framework_Design_v2.md`：早期工业框架草案（已归档）
- `design/archive/Architecture_Final_Review_v2.0.md`：v2.0 终稿评审（基线，已归档）
- `design/archive/Architecture_Final_Review_v2.1.md`：v2.1 终稿评审（对 v2.0 的增量修订，已归档）

### Q: 接口设计文档有两个版本，用哪个？

**A:** 以权威接口为准：
- **权威接口**：`design/Interfaces.md`
- **历史参考**：`design/archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md`（v1.x 时代接口层设计，已归档）

---

## 🗂️ 建议的目录结构（实际落地）

```text
docs/
├── README.md
├── design/
│   ├── Architecture.md
│   ├── Interfaces.md
│   ├── DARE_alignment.md
│   ├── DARE_evidence.yaml
│   └── archive/（历史参考）
│       ├── Architecture_Final_Review_v2.1.md
│       ├── Interface_Layer_Design_v1.1_MCP_and_Builtin.md
│       ├── ARCHITECTURE_COMPARISON.md
│       └── ...（更多历史文档）
├── features/
│   ├── README.md
│   ├── <change-id>.md（每个 change 一个聚合文档）
│   └── archive/
├── governance/
│   ├── Documentation_Management_Model.md
│   └── branch-protection.md
├── guides/
│   ├── Development_Constraints.md
│   ├── Documentation_First_Development_SOP.md
│   └── Engineering_Practice_Guide_Sandbox_and_WORM.md
├── todos/
│   ├── YYYY-MM-DD_<topic>_design_code_gap_analysis.md
│   ├── YYYY-MM-DD_<topic>_design_code_gap_todo.md
│   └── archive/
└── appendix/
    └── Appendix_Industrial_Security_and_Auditing.md
```

---

*最后更新：2026-02-28*
*维护者：DARE Framework Team*
