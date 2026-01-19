# Design: Consolidate Config to Core

## Current Architecture

```
dare_framework/
├── config/                      # Top-level (问题：与 core 平级)
│   ├── config.py                # Config 数据模型
│   ├── config_provider.py       # IConfigProvider 协议 + 合并逻辑
│   ├── component_config.py      # ComponentConfig
│   └── llm_config.py            # LLMConfig
│
├── components/
│   └── config_providers/        # Layer 2 (问题：配置加载先于组件)
│       ├── default_config_provider.py
│       └── layered_config_provider.py
```

### Problems

1. **Layering Violation**: `config/config.py` imports `ComponentType` from `components/plugin_system/` (Layer 0 → Layer 2).

2. **Unnecessary Abstraction**: `IConfigProvider extends IComponent` adds lifecycle complexity (`init/register/close`) for what is essentially a startup-time operation.

3. **Conceptual Chicken-and-Egg**: Config providers are "components" loaded via entrypoints, but entrypoint loading requires config to determine which components to load.

## Target Architecture

```
dare_framework/
├── contracts/
│   └── component_type.py        # ComponentType 枚举（跨层共享）
│
├── core/config/
│   ├── __init__.py              # Facade: Config, ConfigManager, LLMConfig, ComponentConfig
│   ├── models.py                # Config, LLMConfig, ComponentConfig 数据模型
│   └── manager.py               # ConfigManager 分层合并逻辑
```

**文件职责**：
- `contracts/component_type.py`：跨层共享的组件类型枚举，Layer 0/2/3 均可依赖
- `core/config/models.py`：纯配置数据模型
- `core/config/manager.py`：配置管理器，负责分层合并、快照生成

### Key Design Decisions

#### 1. ConfigManager (Not IConfigProvider)

```python
@dataclass
class ConfigManager:
    """Manages layered configuration with deterministic merge semantics."""
    
    system: dict[str, Any] | None = None
    project: dict[str, Any] | None = None
    user: dict[str, Any] | None = None
    session: dict[str, Any] | None = None
    
    def effective(self) -> Config:
        """Return the merged effective configuration."""
        ...
    
    def with_session(self, session: dict[str, Any]) -> "ConfigManager":
        """Return a new manager with session layer applied."""
        ...
```

**Rationale**: No interface, no lifecycle. Just a dataclass with pure functions.

#### 2. ComponentType in Core

Move `ComponentType` enum to `core/config/models.py` to break the circular dependency:

```python
class ComponentType(Enum):
    VALIDATOR = "validator"
    MEMORY = "memory"
    MODEL_ADAPTER = "model_adapter"
    TOOL = "tool"
    SKILL = "skill"
    MCP = "mcp"
    HOOK = "hook"
    PROMPT = "prompt"
```

**Impact**: `components/plugin_system/component_type.py` becomes a re-export or is deleted.

#### 3. Immutable Config Snapshots

`ConfigManager.effective()` returns an immutable `Config` object. Each session gets a snapshot at startup; runtime reload creates a new snapshot without mutating existing sessions.

## Migration Path

1. Create new module at `core/config/`.
2. Copy and simplify models (remove `IComponent` dependency).
3. Update all import paths.
4. Delete old `config/` and `components/config_providers/`.
5. Update tests.

## Alternatives Considered

### Keep `config/` as Top-Level

**Rejected**: Violates the Kernel-centric design. Config loading is a core runtime capability, not a separate concern.

### Keep IConfigProvider Interface

**Rejected**: The abstraction doesn't provide value. There's no need for multiple "providers" — layered merging is the only strategy.

## Test Strategy

1. Unit test `ConfigManager.effective()` with various layer combinations.
2. Integration test that `AgentBuilder` correctly propagates config to sessions.
3. Verify no import errors or circular dependencies.
