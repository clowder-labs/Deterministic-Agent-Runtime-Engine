# Module: skill

> Status: aligned to `dare_framework/skill` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 提供“Agent Skills”格式（SKILL.md）的解析、存储与选择能力。
- 支持通过 `search_skill` 工具检索技能并返回 prompt。

## 2. 关键概念与数据结构

- `Skill`：技能定义（id/name/description/content）。
- `ISkill`：技能接口（非执行，kernel）。
- `ISkillTool`：技能工具标记接口（工具层适配）。
- `ISkillLoader`：技能加载接口（文件系统）。
- `ISkillStore`：技能存储与检索。
- `ISkillSelector`：任务相关性选择器。

## 2.1 Skill 模板（SKILL.md + scripts）

**SKILL.md 结构**：
- YAML Frontmatter（键值对）
- Markdown 正文（技能说明、步骤、约束）

**典型目录结构**：

```text
my_skill/
├── SKILL.md
└── scripts/
    ├── run_tool.py
    └── check.sh
```

**SKILL.md 示例**：

```markdown
---
id: code-review
name: Code Review
description: Review code for defects and risks
---
# Usage
1. Read relevant files
2. Identify defects and risks
3. Provide actionable feedback
```

## 3. 当前实现

- `FileSystemSkillLoader`：从目录扫描 `SKILL.md` + `scripts/`（default）。
- `SkillStore`：内存存储与检索（default）。
- `KeywordSkillSelector`：基于关键词匹配的选择策略（default）。
- `SkillSearchTool`：统一工具 `search_skill`，返回技能 prompt（default）。

## 4. 与其他模块的交互

- **Tool**：`SkillSearchTool` 实现 `ISkillTool`，可注册到 ToolManager。其输出会在执行循环内写入 Context，作为后续 assemble 的 skill prompt。
- **Model/Context**：技能内容可注入 system prompt（需上层实现，当前未内置）。

## 4.1 Skill 模式

- **模式 1：persistent_skill_mode**：单一 agent 挂载 `initial_skill_path`（多 skill 编排策略待定）。
- **模式 2：auto_skill_mode**：单一 agent 注册 `search_skill` 工具（来自 `skill_paths`），工具返回 skill prompt，并在后续 assemble 时注入上下文。

## 5. 约束与限制

- 技能加载仅支持文件系统；无远端技能源。
- Skill 内容注入 Context 尚无默认路径（TODO）。
- 不内置脚本执行（依赖外部工具/流程）。

## 6. 扩展点

- 新 Skill Loader（例如远端仓库）。
- 自定义 Skill Selector（更高级的语义匹配）。
- Skill 内容注入策略（结合 Prompt 管理）。

## 7. TODO / 未决问题

- TODO: 标准化“技能注入上下文”的默认路径与安全边界。
- TODO: skill 检索权限与审计机制。

## 7.1 Config 支持

- `skill_mode`: `"persistent_skill_mode"` | `"auto_skill_mode"`
- `initial_skill_path`: 单个技能路径（用于 persistent 模式）
- `skill_paths`: 技能根目录列表（用于 auto 模式）

## 8. Design Clarifications (2026-02-03)

- Kernel: `ISkill`/`ISkillTool` live in `dare_framework.skill.kernel`.
- Defaults: `FileSystemSkillLoader`/`SkillStore`/`KeywordSkillSelector`/`SkillSearchTool`
  live in `dare_framework.skill.defaults`.
- Doc gap: skill injection path into context/prompt is not specified.
