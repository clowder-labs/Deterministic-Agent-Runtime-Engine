# Module: skill

> Status: detailed design aligned to `dare_framework/skill` (2026-02-25).

## 1. 定位与职责

- 定义 skill（`SKILL.md`）的加载、存储、检索与 prompt 注入策略。
- 通过技能检索工具把“可执行工作流约束”注入模型上下文。

## 2. 依赖与边界

- kernel：`ISkill`, `ISkillTool`
- interfaces：`ISkillLoader`, `ISkillStore`
- types：`Skill`
- 默认实现：
  - `FileSystemSkillLoader`
  - `SkillStore`
  - `SearchSkillTool`
  - `prompt_enricher`（技能注入）
- 边界约束：
  - skill domain 不直接执行脚本，只暴露脚本路径给上层工具链。

## 3. 对外接口（Public Contract）

- `ISkillLoader.load() -> list[Skill]`
- `ISkillStore.list_skills() -> list[Skill]`
- `ISkillStore.get_skill(skill_id) -> Skill | None`
- `ISkillStore.select_for_task(query, limit=5) -> list[Skill]`
- `SearchSkillTool.execute(skill, args="") -> ToolResult`
- prompt enrich API：
  - `enrich_prompt_with_skill(base_prompt, skill)`
  - `enrich_prompt_with_skills(base_prompt, skill_paths)`
  - `enrich_prompt_with_skill_summaries(base_prompt, skills)`

## 4. 关键字段（Core Fields）

- `Skill`
  - `id`, `name`, `description`, `content`
  - `skill_dir: Path | None`
  - `scripts: dict[str, Path]`
- `SearchSkillTool` 输出关键字段
  - `skill_id`, `name`, `description`, `content`
  - `skill_path`, `scripts`, `prompt`, `args`

## 5. 关键流程（Runtime Flow）

```mermaid
flowchart TD
  A["Scan skill_paths"] --> B["FileSystemSkillLoader.load"]
  B --> C["SkillStore index"]
  C --> D["Model requests skill tool"]
  D --> E["SearchSkillTool.resolve + return prompt"]
  E --> F["Context assemble enrich sys_prompt"]
  F --> G["Next LLM call uses enriched prompt"]
```

## 6. 与其他模块的交互

- **Tool**：`SearchSkillTool` 作为 capability 注册到 tool registry。
- **Context/Model**：skill prompt 在 assemble 时注入系统提示。
- **Config**：`skill_paths` 与 `skill_mode` 控制加载模式。

## 7. 约束与限制

- 当前只支持文件系统 skill source。
- 自动注入路径与审批边界仍需进一步标准化。

## 8. TODO / 未决问题

- TODO: 收敛 skill 注入策略（何时注入、注入范围、冲突优先级）。
- TODO: 增加 skill 检索权限控制与审计。
- TODO: 支持远程 skill 仓库与签名校验。

## 能力状态（landed / partial / planned）

- `landed`: 见文档头部 Status 所述的当前已落地基线能力。
- `partial`: 当前实现可用但仍有 TODO/限制（见“约束与限制”与“TODO / 未决问题”）。
- `planned`: 当前文档中的未来增强项，以 TODO 条目为准，未纳入当前实现承诺。

## 最小标准补充（2026-02-27）

### 总体架构
- 模块实现主路径：`dare_framework/skill/`。
- 分层契约遵循 `types.py` / `kernel.py` / `interfaces.py` / `_internal/` 约定；对外语义以本 README 的“对外接口/关键字段/关键流程”章节为准。
- 与全局架构关系：作为 `docs/design/Architecture.md` 中对应 domain 的实现落点，通过 builder 与运行时编排接入。

### 异常与错误处理
- 参数或配置非法时，MUST 显式返回错误（抛出异常或返回失败结果），禁止静默吞错。
- 外部依赖失败（模型/存储/网络/工具）时，优先执行可观测降级策略：记录结构化错误上下文，并在调用边界返回可判定失败。
- 涉及副作用或策略判定的失败路径，MUST 保留审计线索（事件日志或 Hook/Telemetry 记录），以支持回放和排障。

### 测试锚点（Test Anchor）

- `tests/unit/test_skill_store_builder.py`（skill 加载与索引）
- `tests/unit/test_search_skill_tool.py`（skill 检索工具行为）
