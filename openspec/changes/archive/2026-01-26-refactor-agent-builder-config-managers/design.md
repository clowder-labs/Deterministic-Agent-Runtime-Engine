## Context
- 当前 `dare_framework/builder/builder.py` 的 `AgentBuilder` 是 “SimpleChat only” 的最小实现，且强制要求显式注入 model adapter。
- 各域已经存在 `*Manager` 协议接口（例如 `IModelAdapterManager`, `IToolManager`, `IPlannerManager`, `IValidatorManager`, `IRemediatorManager`, `IHookManager`），但 builder 尚未消费这些接口完成 config-driven 装配。
- 需要一套清晰且可验证的 precedence 规则：builder 显式注入优先，其次才是 manager + config 的推导。

## Goals
- 提供一致的开发者 builder API：同一套规则下支持构建 `SimpleChatAgent` 与 `FiveLayerAgent`。
- 支持 config-driven 装配：builder 未显式设置的组件，可通过 `Config` + 对应 manager 自动加载。
- 多加载组件（tools/hooks/validators）使用 extend/merge 语义，并明确 config 过滤边界。
- 保持向后兼容：现有 `AgentBuilder(...)` 调用路径继续可用。

## Non-Goals
- 不在本变更中强制提供默认 entrypoint discovery 的 manager 实现（builder 只依赖 manager 接口；是否基于 entry points 发现由 manager 实现决定）。
- 不在本变更中引入新的 config 元数据机制（例如 hash/source layers）；如未来需要，可在 `IConfigProvider` 上扩展或引入新的 metadata 类型。

## Proposed Public API (sketch)

```python
from dare_framework.builder import Builder
from dare_framework.config.types import Config

config = Config(...)  # effective config
agent = (
    Builder.dare_agent_builder("my-agent")
    .with_config(config)
    .with_managers(
        model_adapter_manager=model_adapter_manager,
        tool_manager=tool_manager,
        planner_manager=planner_manager,
        validator_manager=validator_manager,
        remediator_manager=remediator_manager,
        hook_manager=hook_manager,
    )
    .with_model(explicit_model)  # single-select override (optional)
    .add_tools(tool_a, tool_b)  # multi-load (extend)
    .add_hooks(hook_a)  # multi-load (extend)
    .build()
)
```

Notes:
- 对 multi-load 类别使用 `add_*` 命名，避免 `with_*` 在语义上被误解为“覆盖/替换”。
- 内部基础 builder（不对外公开）应承载所有 builder 共有的基础配置项（例如 `model/config/managers/context/budget/memory/knowledge/tools`），`SimpleChatAgentBuilder` 仅需继承并提供对应的 `build()` 即可。

## Resolution Rules (deterministic)
### Single-select components (e.g., model adapter, planner, remediator)
1. If builder explicitly set the component, use it.
2. Else, if a manager is available, call the manager load method with `config=Config`.
3. If still unresolved and the component is required for the agent variant, raise an error.

### Multi-load components (e.g., tools, hooks, validators)
1. Start from the explicitly injected list (injection order preserved).
2. If a manager is available, load additional instances via the manager with `config=Config`.
3. Apply enable/disable filtering ONLY to the manager-loaded list (boundary rule).
4. Extend: `final = explicit + filtered_manager_loaded`.

## Config Boundary (important)
为满足“builder 显式注入优先”的直觉与可控性：
- `Config.components.<type>.disabled` 等过滤规则 **只对 manager 加载集合生效**。
- builder 显式注入的组件不会被 config 禁用（也不应被 builder 层静默丢弃）。

## Five-Layer ToolGateway Compatibility
`IToolGateway.invoke(...)` 的规范签名需要 `envelope` 参数。当前 `FiveLayerAgent` 的 tool loop 调用需要对齐该签名，才能让 `DefaultToolGateway` 作为默认实现安全工作。该对齐将作为本变更的实现任务之一（并同步更新相关测试 mock 签名）。

## Open Questions
- 是否需要将 `Config` 的具体类型收敛到 `dare_framework.config.types.Config`（而不是 `Any`），并逐步更新各 manager 接口注解？（建议：实现阶段先保持兼容，逐步收敛）
- 是否需要为 multi-load 类别提供 “dedupe by name” 规则？（本变更先不引入；按插入顺序保留即可，去重可作为后续增强）
 - `IConfigProvider` 若未来需要暴露 hash/source layers，是否通过扩展方法（例如 `metadata()`）还是引入新的类型？（本变更先不引入）
