# Proposal: Consolidate Config to Core

## Why

当前配置模块的设计存在以下问题：

1. **职责分散**：`dare_framework/config/` 作为与 `core/` 平级的顶层包，但配置管理本质上是 Kernel 启动和运行的基础能力，应归属于 `core/`。

2. **过度抽象**：`IConfigProvider` 继承自 `IComponent`，引入了插件生命周期（`init/register/close`）的复杂性。但配置加载是启动时的一次性操作，不需要这种抽象。

3. **层次混乱**：`components/config_providers/` 作为 Layer 2 组件存在，但配置加载发生在组件初始化之前，这导致了概念上的先有鸡还是先有蛋的问题。

4. **循环依赖风险**：`config/config.py` 依赖 `components/plugin_system/component_type.py`，违反了分层原则（Layer 3 依赖 Layer 2）。

## What Changes

将配置管理整合到 `core/config/`，作为 Kernel 的核心能力：

1. **移动配置模型**：将 `Config`、`LLMConfig`、`ComponentConfig` 移动到 `core/config/models.py`。

2. **简化配置管理**：用简单的 `ConfigManager` 类替代 `IConfigProvider` 接口，直接支持分层合并逻辑（system < project < user < session）。

3. **删除 Layer 2 配置提供者**：移除 `components/config_providers/` 目录及其 `IConfigProviderManager`。

4. **更新导入路径**：所有依赖 `dare_framework.config` 的模块更新为 `dare_framework.core.config`。

## Impact

- **DX 改善**：配置模块位置更直观，符合 Kernel 核心能力的定位。
- **减少复杂度**：移除不必要的接口抽象和插件生命周期。
- **分层更清晰**：消除 Layer 0 对 Layer 2 的依赖。
- **向后兼容**：保持 `Config` 数据模型的 API 不变，仅更改导入路径。
