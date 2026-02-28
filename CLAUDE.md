
# DARE Framework

## Quick Reference

- **Project Context**: `openspec/project.md` - 技术栈、架构、约定
- **AI Agent Guidelines**: `CONTRIBUTING_AI.md` - AI Agent 协作规则
- **Docs-First SOP**: `docs/guides/Documentation_First_Development_SOP.md` - 文档先行开发流程
- **OpenSpec Workflow**: `openspec/AGENTS.md` - 变更提案流程
- **Design Docs**: `docs/design/` - 架构设计文档

## Core Principles

1. **LLM 输出不可信** - 安全关键字段从 ToolRegistry 派生
2. **状态外化** - 所有状态存 EventLog，不依赖模型记忆
3. **外部验证** - "完成" 由外部验证器判定
4. **增量执行** - 每步提交，留清晰交接物
5. **可审计** - 每个决策有结构化记录

## Architecture (Three Loops)

```
Session Loop   → 跨 context window 持久化
Milestone Loop → Observe → Plan → Validate → Execute → Verify → Remediate
Tool Loop      → Gather → Act → Check → Update (in WorkUnit)
```

## Model Usage Policy

- **代码搜索、文件查找、内容检索**：必须且只能使用 Sonnet 或 Haiku 模型（`claude-sonnet-4-6` / `claude-haiku-4-5-20251001`）
- **思考分析、代码生成**：必须且只能使用 Opus 模型（`claude-opus-4-6`）

## Before You Code

1. Read `openspec/project.md` to understand the project
2. Read `CONTRIBUTING_AI.md` to understand collaboration rules
3. Update `docs/design/` first and satisfy `docs/design/Design_Doc_Minimum_Standard.md`
4. For implementation changes, use `/openspec:proposal` first
