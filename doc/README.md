# DARE Framework 文档导航

> 本文档提供清晰的阅读顺序和文档分类。

---

## 📖 推荐阅读顺序

### 快速上手路径

```
1. 项目概览
   └── /openspec/project.md (项目上下文、技术栈、架构概览)

2. 核心架构
   └── design/Architecture_Final_Review_v1.3.md (⭐ 架构终稿 v1.3，合并 v1.1/v1.2)

3. 接口设计
   └── design/Interface_Layer_Design_v1.1_MCP_and_Builtin.md (⭐ 接口层设计)

4. 示例实现
   └── /examples/coding-agent/ (示例 Agent)

5. 开发指南
   └── /CONTRIBUTING_AI.md (AI Agent 协作规范)
```

---

## 📂 文档分类

### 1️⃣ 核心设计文档（当前有效）

这些是最新的、应该遵循的设计文档：

| 文档 | 作用 | 状态 |
|-----|------|------|
| `Architecture_Final_Review_v1.3.md` | **架构终稿 v1.3**<br/>五层循环、Plan/Execute/Tool、HITL/Remediate、完整接口与数据结构 | ⭐ **当前标准** |
| `Interface_Layer_Design_v1.1_MCP_and_Builtin.md` | **接口层设计**<br/>三层模型、MCP 支持、内置实现、AgentScope 对比 | ⭐ **当前标准** |

### 2️⃣ 对比分析文档

用于理解设计决策和学习其他框架：

| 文档 | 作用 |
|-----|------|
| `Framework_Comparison_PydanticAI.md` | Pydantic AI 对比：学习泛型依赖注入、结构化输出 |
| `anthropic-engineering.md` | Anthropic 工程最佳实践参考 |

### 3️⃣ 历史迭代文档（已归档）

这些是设计演进过程中的历史版本，已被新文档取代：

<details>
<summary>点击展开历史文档列表</summary>

| 文档 | 版本 | 状态 | 被取代者 |
|-----|------|------|---------|
| `Industrial_Agent_Framework_Design_v2.md` | v2.0 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Industrial_Agent_Framework_v2.1_Supplement.md` | v2.1 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Industrial_Agent_Framework_v2.2_Supplement.md` | v2.2 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Industrial_Agent_Framework_v2.3_Supplement.md` | v2.3 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Industrial_Agent_Framework_v2.4_Verifiable_Closures.md` | v2.4 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Agent_Framework_Skeleton_v1.md` | v1.0 | 🗄️ 已归档 | Interface_Layer_Design_v1.1_MCP_and_Builtin.md |
| `Interface_Layer_Design_v1.md` | v1.0 | 🗄️ 已归档 | Interface_Layer_Design_v1.1_MCP_and_Builtin.md |
| `Architecture_Review_and_Gaps.md` | - | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Architecture_Final_Review_v1.md` | v1.0 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Architecture_Final_Review_v1.1.md` | v1.1 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Architecture_Final_Review_v1.2.md` | v1.2 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Architecture_Final_Review_v1_Addendum.md` | - | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Agent_Framework_Loop_Model_v2.2_Final.md` | v2.2 | 🗄️ 已归档 | Architecture_Final_Review_v1.3.md |
| `Agent_Framework_Image_Prompts.md` | - | 🗄️ 已归档 | - |
| `framework-compare.md` | - | 🗄️ 已归档 | Framework_Comparison_PydanticAI.md |

</details>

### 4️⃣ 辅助文档

| 文档 | 作用 |
|-----|------|
| `Gemini_Generated_Image_im2qiuim2qiuim2q.png` | 架构示意图（生成图） |

---

## 🎯 按角色推荐阅读

### 架构师 / Tech Lead

```
1. Architecture_Final_Review_v1.3.md        ← 完整架构
2. Interface_Layer_Design_v1.1_MCP_and_Builtin.md ← 接口设计
3. Framework_Comparison_PydanticAI.md             ← 对比分析
```

### 后端工程师（实现框架）

```
1. Architecture_Final_Review_v1.3.md                  ← 架构总览
2. Interface_Layer_Design_v1.1_MCP_and_Builtin.md    ← 接口设计
3. /openspec/project.md                               ← 技术栈和规范
```

### Agent 开发者（使用框架）

```
1. /examples/coding-agent/README.md              ← 示例 Agent
2. Interface_Layer_Design_v1.1_MCP_and_Builtin.md
   → 第五节：易用性与扩展性                     ← 三种使用模式
3. Architecture_Final_Review_v1.3.md
   → 第七节：使用示例                           ← 代码示例
```

---

## 📋 文档维护规则

### 创建新文档时

1. **主设计文档**：使用版本号（如 `_v2.md`），并在本 README 中更新
2. **补充/对比文档**：直接命名（如 `Framework_Comparison_*.md`）
3. **过时文档**：移动到 `doc/design/archive/` 目录

### 更新文档时

1. 如果是**重大修改**：创建新版本（如 v1.2 → v1.3）
2. 如果是**小修改**：直接更新现有文档
3. 更新本 README 的"最后更新日期"

### 归档标准

文档满足以下任一条件时应归档：
- 被更新版本完全取代
- 不再是"当前标准"
- 仅作历史参考

---

## 🔄 文档演进历史

```
Phase 1: 初始设计 (v2.0 → v2.4)
├── Industrial_Agent_Framework_Design_v2.md
├── v2.1 ~ v2.4 Supplements
└── Agent_Framework_Skeleton_v1.md

Phase 2: 接口设计 (v1.0 → v1.1)
├── Interface_Layer_Design_v1.md
├── Architecture_Review_and_Gaps.md
└── Interface_Layer_Design_v1.1_MCP_and_Builtin.md

Phase 3: 框架对比与融合
├── Framework_Comparison_PydanticAI.md
└── anthropic-engineering.md

Phase 4: 架构终稿 ← 当前
├── Architecture_Final_Review_v1.3.md (⭐ 最新)
├── Architecture_Final_Review_v1.2.md (已归档)
└── Architecture_Final_Review_v1.1.md (已归档)
```

---

## ❓ 常见问题

### Q: 现在应该以哪个文档为准？

**A:** 两个核心文档：
- **架构**：`Architecture_Final_Review_v1.3.md`
- **接口**：`Interface_Layer_Design_v1.1_MCP_and_Builtin.md`

### Q: v2.0 ~ v2.4 的文档还有用吗？

**A:** 仅作历史参考。所有有效内容已合并到 `Architecture_Final_Review_v1.3.md`。

### Q: 接口设计文档有两个版本，用哪个？

**A:** 使用 **v1.1** (`Interface_Layer_Design_v1.1_MCP_and_Builtin.md`)，它包含 MCP 支持和内置实现。

---

## 🗂️ 建议的目录结构整理

```
doc/
├── README.md                          ← 本文档（导航）
│
├── design/                            ← 核心设计文档
│   ├── Architecture_Final_Review_v1.3.md                  ⭐ 架构终稿
│   ├── Interface_Layer_Design_v1.1_MCP_and_Builtin.md     ⭐ 接口设计
│   ├── Framework_Comparison_PydanticAI.md                 对比分析
│   ├── anthropic-engineering.md                           参考资料
│   ├── Gemini_Generated_Image_im2qiuim2qiuim2q.png         架构示意图
│   │
│   └── archive/                       ← 历史文档（归档）
│       ├── Industrial_Agent_Framework_Design_v2.md
│       ├── Industrial_Agent_Framework_v2.1_Supplement.md
│       ├── Industrial_Agent_Framework_v2.2_Supplement.md
│       ├── Industrial_Agent_Framework_v2.3_Supplement.md
│       ├── Industrial_Agent_Framework_v2.4_Verifiable_Closures.md
│       ├── Agent_Framework_Skeleton_v1.md
│       ├── Interface_Layer_Design_v1.md
│       ├── Architecture_Review_and_Gaps.md
│       ├── Architecture_Final_Review_v1.md
│       ├── Architecture_Final_Review_v1.1.md
│       ├── Architecture_Final_Review_v1.2.md
│       ├── Architecture_Final_Review_v1_Addendum.md
│       ├── Agent_Framework_Loop_Model_v2.2_Final.md
│       ├── Agent_Framework_Image_Prompts.md
│       └── framework-compare.md
```

---

*最后更新：2025-12-23*
*维护者：DARE Framework Team*
