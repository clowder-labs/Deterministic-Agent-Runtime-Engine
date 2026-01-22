# DARE Framework 文档导航

> 本文档提供清晰的阅读顺序和文档分类（以 `/doc/` 为范围）。  
> **当前标准：v3.4（对应 `dare_framework3_4/`）**

---

## 📖 推荐阅读顺序（v3.4）

```text
1. v3.4 架构终稿（当前标准）
   └── design/Architecture_Final_Review_v3.4.md

2. v3.4 代码实现（以代码为准）
   └── dare_framework3_4/

3. v3.4 最小示例
   └── examples/basic-chat/chat3.4.py

4. 开发规范与工程实践
   ├── /CONTRIBUTING_AI.md
   ├── guides/Development_Constraints.md
   └── guides/Engineering_Practice_Guide_Sandbox_and_WORM.md
```

---

## 📂 文档分类

### 1️⃣ 核心设计文档（当前实现标准）

| 文档 | 作用 | 状态 |
|---|---|---|
| `design/Architecture_Final_Review_v3.4.md` | **架构终稿评审 v3.4（Final）**<br/>Context-centric 最小集；与 `dare_framework3_4/` 逐项对齐 | ⭐ 当前标准 |
| `dare_framework3_4/` | **v3.4 代码侧真相**<br/>接口/实现以代码为准 | ⭐ 当前标准 |

### 2️⃣ 附录与工程实践

| 文档 | 作用 |
|---|---|
| `appendix/Appendix_Industrial_Security_and_Auditing.md` | 工业级安全与审计附录（历史沉淀，可复用） |
| `guides/Engineering_Practice_Guide_Sandbox_and_WORM.md` | 工程实践指南：沙箱执行隔离、WORM 落地与核查 |
| `guides/Development_Constraints.md` | 开发约束：架构约束、测试/日志/命名/信任边界等 |

---

## 🗄️ 归档材料（历史参考）

v3.4 之前的设计与对比材料已统一归档到 `design/archive/`，仅用于追溯演进过程，不作为“当前标准”。

---

## ❓ 常见问题

### Q: 现在应该以哪个文档/代码为准？

**A:** 以 v3.4 为准：
- 设计：`design/Architecture_Final_Review_v3.4.md`
- 代码：`dare_framework3_4/`

---

*最后更新：2026-01-22*  
