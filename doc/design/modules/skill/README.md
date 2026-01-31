# Module: skill

> Status: aligned to `dare_framework/skill` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 提供“Agent Skills”格式（SKILL.md）的解析、存储与选择能力。
- 支持将技能脚本暴露为工具（`run_skill_script`）。

## 2. 关键概念与数据结构

- `Skill`：技能定义（id/name/description/content/metadata）。
- `ISkillLoader`：技能加载接口（文件系统）。
- `ISkillStore`：技能存储与检索。
- `ISkillSelector`：任务相关性选择器。

## 3. 当前实现

- `FileSystemSkillLoader`：从目录扫描 `SKILL.md` + `scripts/`。
- `SkillStore`：内存存储与检索。
- `KeywordSkillSelector`：基于关键词匹配的选择策略。
- `SkillScriptRunner`：统一工具 `run_skill_script` 执行脚本。

## 4. 与其他模块的交互

- **Tool**：`SkillScriptRunner` 实现 `ITool`，可注册到 ToolManager。
- **Model/Context**：技能内容可注入 system prompt（需上层实现，当前未内置）。

## 5. 约束与限制

- 技能加载仅支持文件系统；无远端技能源。
- Skill 内容注入 Context 尚无默认路径（TODO）。
- 脚本执行默认需要审批（`requires_approval=True`）。

## 6. 扩展点

- 新 Skill Loader（例如远端仓库）。
- 自定义 Skill Selector（更高级的语义匹配）。
- Skill 内容注入策略（结合 Prompt 管理）。

## 7. TODO / 未决问题

- TODO: 标准化“技能注入上下文”的默认路径与安全边界。
- TODO: skill 执行权限与审计机制。
