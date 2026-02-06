# Module: config

> Status: aligned to `dare_framework/config` (2026-01-31).

## 1. 定位与职责

- 提供全局配置模型与加载策略。
- 支持多层配置合并（user + workspace）。
- 为 Manager/Builder 提供组件启用/禁用与参数解析。

## 2. 关键概念与数据结构

- `Config`：统一配置入口（llm/tools/components/workspace_dir/user_dir/skill_mode/skill_paths/initial_skill_path）。
- `LLMConfig` / `ProxyConfig`：模型连接与代理配置。
- `ComponentConfig`：组件级 enable/disable 配置。

## 3. 关键接口与实现

- Kernel：`IConfigProvider`（`dare_framework/config/kernel.py`）
- 默认实现：`FileConfigProvider`（`dare_framework/config/file_config_provider.py`）

## 4. 配置层级与合并规则

- 默认配置文件：`.dare/config.json`
- 合并顺序：**user 层 → workspace 层**（workspace 覆盖 user）
- 自动写入空配置文件（当文件不存在时）。

## 5. 与其他模块的交互

- **Model**：`Config.llm` 决定默认 adapter/endpoint/api_key。
- **Tool**：`Config.tools` 提供 tool-specific config；`components` 控制启用/禁用。
- **Builder/Manager**：按组件类型过滤/选择组件。
- **Skill**：`skill_mode` 控制 skill 模式；`skill_paths` 提供技能目录集合；`initial_skill_path` 用于 agent 模式挂载单一 skill。

## 6. 约束与限制

- 仅支持 JSON 配置文件。
- `allow_tools` / `allow_mcps` 未在 ToolManager 中强制执行（TODO）。

## 7. TODO / 未决问题

- TODO: 增加环境变量或多格式配置支持（YAML/TOML）。
- TODO: enforce allowlists（allow_tools/allow_mcps）。
- TODO: 配置热更新与订阅机制。

## 8. Design Clarifications (2026-02-03)

- Doc gap: component-level config schema is not defined; `component_config()` returns `Any`.
- Impl gap: tighten config typing (at least `dict[str, Any]`) for component configs.
- Surface: `FileConfigProvider` is exposed as a default implementation in the config facade.
