# DARE Framework 文档导航

> 本文档提供清晰的阅读顺序和文档分类（以 `/doc/` 为范围）。

---

## 📖 推荐阅读顺序

### 快速上手（以 v2.1 为当前实现标准）

```text
1. 项目概览
   └── /openspec/project.md (项目上下文、技术栈、架构概览)

2. 核心架构（当前标准）
   └── design/Architecture_Final_Review_v2.1.md

3. 接口设计（当前标准）
   ├── design/Architecture_Final_Review_v2.1.md（v2.1 Kernel contracts）
   └── dare_framework/core/（代码侧接口定义与默认实现）

4. 示例实现
   └── /examples/coding-agent/ (示例 Agent)

5. 开发规范
   ├── /CONTRIBUTING_AI.md (AI Agent 协作规范)
   └── guides/Development_Constraints.md (开发约束清单)
```

### 历史参考（v1.3）

```text
1. v1.3 架构终稿（历史参考）
   └── design/Architecture_Final_Review_v1.3.md

2. v1.1 接口层设计（历史参考）
   └── design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md
```

---

## 📂 文档分类

### 1️⃣ 核心设计文档（当前实现标准）

| 文档 | 作用 | 状态 |
|---|---|---|
| `design/Architecture_Final_Review_v2.1.md` | **架构终稿评审 v2.1**<br/>Kernel 化、上下文工程、协议适配层、长任务控制面 | ⭐ 当前标准 |
| `dare_framework/core/` | **Kernel 代码契约（v2）**<br/>接口定义 + 默认实现（以代码为准） | ⭐ 当前标准 |

### 2️⃣ 历史架构与接口（v1.x）

| 文档 | 作用 | 状态 |
|---|---|---|
| `design/Architecture_Final_Review_v1.3.md` | **架构终稿 v1.3**<br/>五层循环、Plan/Execute/Tool、HITL/Remediate | 🗄️ 历史参考 |
| `design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md` | **接口层设计 v1.1**<br/>三层模型、MCP 支持、内置实现 | 🗄️ 历史参考 |

### 3️⃣ 对比分析文档

| 文档 | 作用 |
|---|---|
| `design/Framework_Comparison_PydanticAI.md` | PydanticAI 对比：泛型依赖注入、结构化输出、类型安全 |
| `design/Framework_Comparison_AgentScope.md` | AgentScope 对比：平台化能力、Runtime/Studio、DARE 差异化 |
| `design/anthropic-engineering.md` | Anthropic 工程最佳实践参考 |

### 4️⃣ 辅助文档

| 文档 | 作用 |
|---|---|
| `design/Gemini_Generated_Image_im2qiuim2qiuim2q.png` | 架构示意图（生成图） |

### 5️⃣ 附录与工程实践

| 文档 | 作用 |
|---|---|
| `appendix/Appendix_Industrial_Security_and_Auditing.md` | 工业级安全与审计附录：WORM、Merkle 批次密封、审计复验 |
| `guides/Engineering_Practice_Guide_Sandbox_and_WORM.md` | 工程实践指南：沙箱执行隔离（seccomp/网络/镜像）、WORM 落地与核查 |
| `guides/Development_Constraints.md` | 开发约束：架构不破坏、测试必备、日志/命名/复用/信任边界等硬性要求 |

---

## 🗄️ 归档材料（历史参考）

这些文档用于追溯设计演进过程，不作为“当前标准”。归档文件位于 `design/archive/`。

<details>
<summary>点击展开归档列表</summary>

### 设计版本归档（已被 v1.3 取代）

> 说明：这里的 `Industrial_Agent_Framework_* v2.x` 属于更早期的工业框架草案（历史资料），与“下一代架构草案 v2.0（Kernel 化）”不是同一条版本线；请以文件名与目录为准。

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

</details>

---

## 🎯 按角色推荐阅读

### 架构师 / Tech Lead

```text
1. design/Architecture_Final_Review_v2.0.md
2. dare_framework/core/（Kernel contract 代码侧真相）
3. /openspec/project.md（项目约束与变更流程）
4. guides/Development_Constraints.md
5. design/Architecture_Final_Review_v1.3.md / design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md（历史参考）
```

### 后端工程师（实现框架）

```text
1. design/Architecture_Final_Review_v2.0.md
2. dare_framework/core/
3. /openspec/project.md
4. guides/Development_Constraints.md
```

### Agent 开发者（使用框架）

```text
1. /examples/coding-agent/README.md
2. design/Architecture_Final_Review_v2.0.md
3. dare_framework/builder.py（组装 API）
```

---

## 📋 文档维护规则

### 创建新文档时

1. **主设计文档**：使用版本号（如 `_v2.0.md`），并在本 README 中更新
2. **补充/对比文档**：使用清晰主题命名（如 `Framework_Comparison_*.md`）
3. **过程材料/过时文档**：移动到 `doc/design/archive/` 目录

### 更新文档时

1. 如果是**重大修改**：创建新版本（如 v1.2 → v1.3）
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
Phase 1: 初始设计（Industrial Agent Framework v2.0 → v2.4，已归档）
├── Industrial_Agent_Framework_Design_v2.md
└── v2.1 ~ v2.4 Supplements

Phase 2: 接口设计（v1.0 → v1.1）
├── Interface_Layer_Design_v1.md
└── Interface_Layer_Design_v1.1_MCP_and_Builtin.md

Phase 3: 框架对比与融合
├── Framework_Comparison_PydanticAI.md
├── Framework_Comparison_AgentScope.md
└── anthropic-engineering.md

Phase 4: 架构终稿 v1.3（历史参考）
└── Architecture_Final_Review_v1.3.md

Phase 5: 架构内核化 v2.x（当前实现标准：v2.1）
├── Architecture_v2.0_Proposal.md
├── Architecture_Final_Review_v2.0.md
└── Architecture_Final_Review_v2.1.md
```

---

## ❓ 常见问题

### Q: 现在应该以哪个文档为准？

**A:** 当前实现标准以 v2 为准：
- **架构**：`design/Architecture_Final_Review_v2.1.md`
- **接口**：`dare_framework/core/`（以代码为准）

### Q: 为什么会看到两个 “v2.0”？

**A:** 这是历史原因导致的命名重叠：
- `design/archive/Industrial_Agent_Framework_Design_v2.md`：早期工业框架草案（已归档）
- `design/Architecture_Final_Review_v2.0.md`：v2.0 终稿评审（基线）
- `design/Architecture_Final_Review_v2.1.md`：v2.1 终稿评审（对 v2.0 的增量修订）

### Q: 接口设计文档有两个版本，用哪个？

**A:** 当前以 v2 为准：
- **Kernel contracts**：`design/Architecture_Final_Review_v2.1.md` + `dare_framework/core/`（以代码为准）
- **历史参考**：`design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md`（v1.x 时代接口层设计）

---

## 🗂️ 建议的目录结构（实际落地）

```text
doc/
├── README.md
├── design/
│   ├── Architecture_Final_Review_v1.3.md
│   ├── Architecture_Final_Review_v2.0.md
│   ├── Architecture_Final_Review_v2.1.md
│   ├── Architecture_v2.0_Proposal.md
│   ├── Interface_Layer_Design_v1.1_MCP_and_Builtin.md
│   ├── Framework_Comparison_PydanticAI.md
│   ├── Framework_Comparison_AgentScope.md
│   ├── anthropic-engineering.md
│   ├── Gemini_Generated_Image_im2qiuim2qiuim2q.png
│   └── archive/
│       ├── Architecture_v2.0_Claude_Feedback_Analysis.md
│       ├── Architecture_v1.3_Claude_Feedback_1.md
│       ├── Architecture_v1.3_Claude_Feedback_2.md
│       └── ...（更多历史文档）
├── guides/
│   ├── Development_Constraints.md
│   └── Engineering_Practice_Guide_Sandbox_and_WORM.md
└── appendix/
    └── Appendix_Industrial_Security_and_Auditing.md
```

---

*最后更新：2026-01-18*  
*维护者：DARE Framework Team*
