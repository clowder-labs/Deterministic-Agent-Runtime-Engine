"""Agent builders for composing agents deterministically.

This module provides three public builders:
- SimpleChatAgentBuilder: builds SimpleChatAgent (simple chat, no tool execution)
- ReactAgentBuilder: builds ReactAgent (ReAct tool loop: execute tool_calls and re-call model)
- DareAgentBuilder: builds DareAgent (five-layer orchestration)

All builder variants share the same precedence rules:
1) Explicit builder injection wins (highest precedence).
2) Missing components may be resolved via injected domain managers + Config.
3) Multi-load component categories use extend semantics.

MCP Integration:
- Call build() (async) with with_config(config); when config.mcp_paths is set,
  MCP is loaded inside build() before assembling the agent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, TypeVar

from dare_framework.agent._internal.five_layer import DareAgent
from dare_framework.agent._internal.react_agent import ReactAgent
from dare_framework.agent._internal.simple_chat import SimpleChatAgent
from dare_framework.config.types import Config
from dare_framework.context import Budget, Context
from dare_framework.event.kernel import IEventLog
from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.kernel import IHook
from dare_framework.infra.component import ComponentType
from dare_framework.knowledge import IKnowledge
from dare_framework.memory import ILongTermMemory, IShortTermMemory
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.interfaces import IModelAdapterManager, IPromptStore
from dare_framework.model.types import Prompt
from dare_framework.model.factories import (
    create_default_model_adapter_manager,
    create_default_prompt_store,
)
from dare_framework.plan._internal.composite_validator import CompositeValidator
from dare_framework.plan.interfaces import (
    IPlanner,
    IPlannerManager,
    IRemediator,
    IRemediatorManager,
    IValidator,
    IValidatorManager,
)
from dare_framework.tool._internal.managers.tool_manager import ToolManager
from dare_framework.tool.interfaces import ITool, IToolProvider, RunContext
from dare_framework.tool.kernel import IExecutionControl, IToolGateway, IToolManager

logger = logging.getLogger(__name__)

TBuilder = TypeVar("TBuilder", bound="_BaseAgentBuilder")


class _BaseAgentBuilder:
    """Internal base builder shared by all public builder variants."""

    def __init__(self, name: str) -> None:
        self._name = name

        # Shared configuration surface (used by all builder variants).
        self._config: Config | None = None
        self._model_adapter_manager: IModelAdapterManager | None = None
        self._planner_manager: IPlannerManager | None = None
        self._validator_manager: IValidatorManager | None = None
        self._remediator_manager: IRemediatorManager | None = None
        self._hook_manager: IHookManager | None = None

        # Core components (commonly used across agent variants).
        self._model: IModelAdapter | None = None
        self._context: Context | None = None
        self._budget: Budget | None = None
        self._short_term_memory: IShortTermMemory | None = None
        self._long_term_memory: ILongTermMemory | None = None
        self._knowledge: IKnowledge | None = None
        self._prompt_store: IPromptStore | None = None
        self._prompt_override: Prompt | None = None
        self._prompt_id_override: str | None = None

        # Tool wiring (shared across variants).
        self._tools: list[ITool] = []
        self._tool_gateway: IToolGateway | None = None
        self._tool_provider: IToolProvider | None = None
        self._run_context_factory: Callable[[], RunContext[Any]] = self._default_run_context

        # MCP toolkit (optional, provides MCP-backed tools).
        self._mcp_toolkit: IToolProvider | None = None

        # Initial skill path (None = not set; single path for one skill).
        self._initial_skill_path: str | None = None

    def _manager_config(self) -> Config | None:
        """Return the Config passed to managers."""

        return self._config

    # ---------------------------------------------------------------------
    # Shared "base" configuration API
    # ---------------------------------------------------------------------

    def with_config(self: TBuilder, config: Config) -> TBuilder:
        self._config = config
        return self

    def with_managers(
        self: TBuilder,
        *,
        model_adapter_manager: IModelAdapterManager | None = None,
        planner_manager: IPlannerManager | None = None,
        validator_manager: IValidatorManager | None = None,
        remediator_manager: IRemediatorManager | None = None,
        hook_manager: IHookManager | None = None,
    ) -> TBuilder:
        """Inject component managers for config-driven resolution.

        Managers are only used when the corresponding component is not explicitly provided
        via builder methods (precedence rule).
        """
        if model_adapter_manager is not None:
            self._model_adapter_manager = model_adapter_manager
        if planner_manager is not None:
            self._planner_manager = planner_manager
        if validator_manager is not None:
            self._validator_manager = validator_manager
        if remediator_manager is not None:
            self._remediator_manager = remediator_manager
        if hook_manager is not None:
            self._hook_manager = hook_manager
        return self

    def with_model(self: TBuilder, model: IModelAdapter) -> TBuilder:
        self._model = model
        return self

    def with_prompt_store(self: TBuilder, store: IPromptStore) -> TBuilder:
        self._prompt_store = store
        return self

    def with_prompt(self: TBuilder, prompt: Prompt) -> TBuilder:
        self._prompt_override = prompt
        self._prompt_id_override = None
        return self

    def with_prompt_id(self: TBuilder, prompt_id: str) -> TBuilder:
        self._prompt_id_override = prompt_id
        self._prompt_override = None
        return self

    def with_context(self: TBuilder, context: Context) -> TBuilder:
        self._context = context
        return self

    def with_budget(self: TBuilder, budget: Budget) -> TBuilder:
        self._budget = budget
        return self

    def with_short_term_memory(self: TBuilder, memory: IShortTermMemory) -> TBuilder:
        self._short_term_memory = memory
        return self

    def with_long_term_memory(self: TBuilder, memory: ILongTermMemory) -> TBuilder:
        self._long_term_memory = memory
        return self

    def with_knowledge(self: TBuilder, knowledge: IKnowledge) -> TBuilder:
        self._knowledge = knowledge
        return self

    def add_tools(self: TBuilder, *tools: ITool) -> TBuilder:
        self._tools.extend(tools)
        return self

    def with_tool_gateway(self: TBuilder, gateway: IToolGateway) -> TBuilder:
        self._tool_gateway = gateway
        return self

    def with_tool_provider(self: TBuilder, provider: IToolProvider) -> TBuilder:
        self._tool_provider = provider
        return self

    def with_run_context_factory(self: TBuilder, factory: Callable[[], RunContext[Any]]) -> TBuilder:
        self._run_context_factory = factory
        return self

    def with_skill(self: TBuilder, path: str | Path) -> TBuilder:
        """Set initial skill path (one skill). Loaded at build, mounted on context."""
        self._initial_skill_path = str(path)
        return self

    async def build(self) -> Any:
        """Build the agent. When with_config() was used and config.mcp_paths is set, loads MCP inside build()."""
        if self._config is not None and getattr(self._config, "mcp_paths", None):
            self._mcp_toolkit = await load_mcp_toolkit(self._config)
        return self._build_impl()

    def _build_impl(self) -> Any:
        """Override in subclasses to perform the actual build. Called by build() after MCP load."""
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # Shared helper utilities
    # ---------------------------------------------------------------------

    def _apply_context_overrides(self, context: Context) -> None:
        """Apply optional overrides to a provided context instance."""
        if self._budget is not None:
            context.budget = self._budget
        if self._short_term_memory is not None:
            context.short_term_memory = self._short_term_memory
        if self._long_term_memory is not None:
            context.long_term_memory = self._long_term_memory
        if self._knowledge is not None:
            context.knowledge = self._knowledge

    def _default_run_context(self) -> RunContext[Any]:
        """Create a default run context for tool invocation."""
        return RunContext(deps=None, metadata={"agent": self._name})

    def _effective_config(self) -> Config:
        return self._config or Config()

    def _resolve_prompt_store(self) -> IPromptStore:
        if self._prompt_store is not None:
            return self._prompt_store
        return create_default_prompt_store(self._effective_config())

    def _resolve_sys_prompt(self, model: IModelAdapter) -> Prompt | None:
        if self._prompt_override is not None:
            return self._prompt_override

        model_name = getattr(model, "name", None)
        if not model_name:
            raise ValueError("Model adapter must define a stable name for prompt resolution")

        store = self._resolve_prompt_store()

        prompt_id = self._prompt_id_override
        if prompt_id is None:
            prompt_id = self._effective_config().default_prompt_id
        if prompt_id is None:
            prompt_id = "base.system"

        try:
            return store.get(prompt_id, model=model_name)
        except KeyError as exc:
            raise ValueError(f"Prompt not found: {prompt_id}") from exc
    def _ensure_tool_gateway(self, tools: list[ITool]) -> IToolGateway | None:
        """Return a ToolGateway if tool wiring requires one."""
        if self._tool_gateway is not None:
            return self._tool_gateway
        if tools:
            self._tool_gateway = ToolManager(context_factory=self._run_context_factory)
            return self._tool_gateway
        return None

    def _ensure_tool_provider(
        self,
        manager: IToolManager | None,
        explicit_tools: list[ITool],
    ) -> IToolProvider | None:
        """Return a tool provider for Context.listing_tools()."""
        if self._tool_provider is not None:
            return self._tool_provider
        if manager is not None:
            if self._config is None:
                return manager
            return _ConfiguredToolProvider(
                manager=manager,
                config=self._config,
                explicit_names={tool.name for tool in explicit_tools},
            )
        if isinstance(self._tool_gateway, IToolProvider):
            return self._tool_gateway
        return None

    def _ensure_tool_manager(self, tools: list[ITool]) -> IToolManager | None:
        gateway = self._ensure_tool_gateway(tools)
        if tools and gateway is not None and not isinstance(gateway, IToolManager):
            raise TypeError(
                "tool_gateway must implement IToolManager when tools are injected. "
                "Provide ToolManager or avoid add_tools()."
            )
        return gateway if isinstance(gateway, IToolManager) else None

    def _register_tools_with_manager(self, manager: IToolManager | None, tools: list[ITool]) -> None:
        """将合并后的工具列表（含本地 + MCP）全部注册进 ToolManager，供 invoke 按 name 查找。"""
        if manager is None:
            return
        for tool in tools:
            manager.register_tool(tool)

    def _resolved_model(self) -> IModelAdapter:
        if self._model is not None:
            return self._model

        manager = self._model_adapter_manager or create_default_model_adapter_manager(self._manager_config())
        if manager is None:
            raise ValueError("Builder requires a model adapter (explicit or manager-resolved)")

        candidate = manager.load_model_adapter(config=self._manager_config())
        if candidate is None:
            raise ValueError("Model adapter manager did not return an IModelAdapter")
        return candidate

    def _load_initial_skill_and_mount(self, context: Context) -> None:
        """Load skill from initial_skill_path and mount on context."""
        path = self._initial_skill_path if self._initial_skill_path is not None else self._effective_config().initial_skill_path
        if not path:
            return
        from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader

        loader = FileSystemSkillLoader(Path(path))
        skills = loader.load()
        if skills:
            context.set_skill(skills[0])

    def _resolved_tools(self) -> list[ITool]:
        """Resolve and merge all tools: 本地(explicit) + MCP(mcp_toolkit.list_tools) + manager-discovered.

        MCP 工具在此处与本地 add_tools() 注入的 tool 合并为同一 list，
        随后由 _register_tools_with_manager() 统一注册进 ToolManager。
        """
        explicit = list(self._tools)
        explicit_names = {tool.name for tool in explicit}

        # MCP: 从 mcp_toolkit 拉取工具列表，与 explicit 合并（按 allowmcps 过滤、去重）
        mcp_tools: list[ITool] = []
        if self._mcp_toolkit is not None:
            config = self._effective_config()
            allowmcps = set(config.allowmcps) if config.allowmcps else None

            for tool in self._mcp_toolkit.list_tools():
                # Extract MCP server name from tool name (format: "server:tool")
                if allowmcps is not None:
                    server_name = tool.name.split(":")[0] if ":" in tool.name else tool.name
                    if server_name not in allowmcps:
                        continue

                if tool.name not in explicit_names:
                    mcp_tools.append(tool)
                    explicit_names.add(tool.name)

            if mcp_tools:
                logger.debug(f"Loaded {len(mcp_tools)} MCP tools")

        # Add manager-discovered tools
        manager = self._tool_gateway if isinstance(self._tool_gateway, IToolManager) else None
        if manager is None:
            return [*explicit, *mcp_tools]

        discovered = manager.load_tools(config=self._manager_config())
        manager_tools = [
            tool
            for tool in discovered
            if tool.name not in explicit_names
            and (self._config is None or self._config.is_component_enabled(tool))
        ]
        return [*explicit, *mcp_tools, *manager_tools]


class SimpleChatAgentBuilder(_BaseAgentBuilder):
    """Builder for SimpleChatAgent."""

    def _build_impl(self) -> SimpleChatAgent:
        model = self._resolved_model()
        sys_prompt = self._resolve_sys_prompt(model)

        tools = self._resolved_tools()
        manager = self._ensure_tool_manager(tools)
        self._register_tools_with_manager(manager, tools)
        tool_gateway = self._ensure_tool_gateway(tools)

        tool_provider = self._ensure_tool_provider(manager, tools)

        if self._context is None:
            context = Context(
                id=f"context_{self._name}",
                short_term_memory=self._short_term_memory,
                long_term_memory=self._long_term_memory,
                knowledge=self._knowledge,
                budget=self._budget or Budget(),
            )
            if tool_provider is not None:
                context._tool_provider = tool_provider
            context._sys_prompt = sys_prompt
            self._load_initial_skill_and_mount(context)
            return SimpleChatAgent(
                name=self._name,
                model=model,
                context=context,
            )

        self._apply_context_overrides(self._context)
        if tool_provider is not None:
            setattr(self._context, "_tool_provider", tool_provider)
        setattr(self._context, "_sys_prompt", sys_prompt)
        self._load_initial_skill_and_mount(self._context)

        return SimpleChatAgent(
            name=self._name,
            model=model,
            context=self._context,
        )


class ReactAgentBuilder(_BaseAgentBuilder):
    """Builder for ReactAgent (ReAct tool loop)."""

    def _build_impl(self) -> ReactAgent:
        model = self._resolved_model()
        sys_prompt = self._resolve_sys_prompt(model)

        tools = self._resolved_tools()
        manager = self._ensure_tool_manager(tools)
        self._register_tools_with_manager(manager, tools)
        self._ensure_tool_gateway(tools)
        tool_provider = self._ensure_tool_provider(manager, tools)

        if self._context is None:
            context = Context(
                id=f"context_{self._name}",
                short_term_memory=self._short_term_memory,
                long_term_memory=self._long_term_memory,
                knowledge=self._knowledge,
                budget=self._budget or Budget(),
            )
            if tool_provider is not None:
                context._tool_provider = tool_provider
            context._sys_prompt = sys_prompt
            self._load_initial_skill_and_mount(context)
            return ReactAgent(
                name=self._name,
                model=model,
                context=context,
            )

        self._apply_context_overrides(self._context)
        if tool_provider is not None:
            setattr(self._context, "_tool_provider", tool_provider)
        setattr(self._context, "_sys_prompt", sys_prompt)
        self._load_initial_skill_and_mount(self._context)

        return ReactAgent(
            name=self._name,
            model=model,
            context=self._context,
        )


class DareAgentBuilder(_BaseAgentBuilder):
    """Builder for DareAgent (five-layer orchestration)."""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self._planner: IPlanner | None = None
        self._validators: list[IValidator] = []
        self._remediator: IRemediator | None = None

        self._event_log: IEventLog | None = None
        self._execution_control: IExecutionControl | None = None
        self._hooks: list[IHook] = []
        self._verbose: bool = False

    def with_planner(self, planner: IPlanner) -> DareAgentBuilder:
        self._planner = planner
        return self

    def add_validators(self, *validators: IValidator) -> DareAgentBuilder:
        self._validators.extend(validators)
        return self

    def with_remediator(self, remediator: IRemediator) -> DareAgentBuilder:
        self._remediator = remediator
        return self

    def with_event_log(self, event_log: IEventLog) -> DareAgentBuilder:
        self._event_log = event_log
        return self

    def with_execution_control(self, execution_control: IExecutionControl) -> DareAgentBuilder:
        self._execution_control = execution_control
        return self

    def add_hooks(self, *hooks: IHook) -> DareAgentBuilder:
        self._hooks.extend(hooks)
        return self

    def with_verbose(self, verbose: bool = True) -> DareAgentBuilder:
        self._verbose = verbose
        return self

    def _build_impl(self) -> DareAgent:
        model = self._resolved_model()
        sys_prompt = self._resolve_sys_prompt(model)

        tools = self._resolved_tools()
        manager = self._ensure_tool_manager(tools)
        self._register_tools_with_manager(manager, tools)
        tool_gateway = self._ensure_tool_gateway(tools)
        tool_provider = self._ensure_tool_provider(manager, tools)

        planner = self._planner
        if planner is None:
            manager = self._planner_manager
            if manager is not None:
                candidate = manager.load_planner(config=self._manager_config())
                if candidate is not None:
                    planner = candidate

        validators = list(self._validators)
        manager = self._validator_manager
        if manager is not None:
            discovered = manager.load_validators(config=self._manager_config())
            validators.extend(
                [v for v in discovered if self._config is None or self._config.is_component_enabled(v)]
            )

        validator: IValidator | None
        if not validators:
            validator = None
        elif len(validators) == 1:
            validator = validators[0]
        else:
            validator = CompositeValidator(validators)

        remediator = self._remediator
        manager = self._remediator_manager
        if remediator is None and manager is not None:
            candidate = manager.load_remediator(config=self._manager_config())
            if candidate is not None:
                remediator = candidate

        explicit_hooks = list(self._hooks)
        resolved_hooks = list(explicit_hooks)

        manager = self._hook_manager
        if manager is not None:
            discovered = manager.load_hooks(config=self._manager_config())
            resolved_hooks.extend(
                [hook for hook in discovered if self._config is None or self._config.is_component_enabled(hook)]
            )

        hooks = resolved_hooks or None

        if self._context is None:
            context = Context(
                id=f"context_{self._name}",
                short_term_memory=self._short_term_memory,
                long_term_memory=self._long_term_memory,
                knowledge=self._knowledge,
                budget=self._budget or Budget(),
            )
            if tool_provider is not None:
                context._tool_provider = tool_provider
            context._sys_prompt = sys_prompt
            self._load_initial_skill_and_mount(context)
            return DareAgent(
                name=self._name,
                model=model,
                context=context,
                tools=tool_provider,
                tool_gateway=tool_gateway,
                execution_control=self._execution_control,
                planner=planner,
                validator=validator,
                remediator=remediator,
                event_log=self._event_log,
                hooks=hooks,
                verbose=self._verbose,
            )

        self._apply_context_overrides(self._context)
        if tool_provider is not None:
            setattr(self._context, "_tool_provider", tool_provider)
        setattr(self._context, "_sys_prompt", sys_prompt)
        self._load_initial_skill_and_mount(self._context)

        return DareAgent(
            name=self._name,
            model=model,
            context=self._context,
            tools=tool_provider,
            tool_gateway=tool_gateway,
            execution_control=self._execution_control,
            planner=planner,
            validator=validator,
            remediator=remediator,
            event_log=self._event_log,
            hooks=hooks,
            verbose=self._verbose,
        )


__all__ = ["DareAgentBuilder", "ReactAgentBuilder", "SimpleChatAgentBuilder"]


async def load_mcp_toolkit(
    config: Config | None = None,
    *,
    paths: list[str | Path] | None = None,
) -> IToolProvider:
    """Load and initialize an MCP toolkit from configuration.

    Scans configured directories for MCP server definitions, creates clients,
    connects to servers, and returns an initialized MCPToolkit.

    Args:
        config: Configuration with mcp_paths and allowmcps settings.
                If None, uses default Config.
        paths: Explicit list of paths to scan. Overrides config.mcp_paths.

    Returns:
        Initialized MCPToolkit (implements IToolProvider).

    Example (called internally by builder.build() when config.mcp_paths is set):
        config = Config(mcp_paths=[".dare/mcp"], ...)
        builder = DareAgentBuilder("my_agent").with_config(config)
        agent = await builder.build()

    Note:
        Remember to close the toolkit when done to disconnect MCP clients:
            await toolkit.close()
    """
    from dare_framework.mcp.factory import create_mcp_clients
    from dare_framework.mcp.loader import load_mcp_configs
    from dare_framework.tool._internal.toolkits.mcp_toolkit import MCPToolkit

    if config is None:
        config = Config()

    # Determine scan paths
    if paths is None:
        paths = config.mcp_paths if config.mcp_paths else None

    # Load MCP server configurations
    mcp_configs = load_mcp_configs(
        paths=paths,
        workspace_dir=config.workspace_dir,
        user_dir=config.user_dir,
    )

    if not mcp_configs:
        logger.debug("No MCP configurations found")
        return MCPToolkit([])

    # Filter by allowmcps if specified
    if config.allowmcps:
        allowed = set(config.allowmcps)
        mcp_configs = [c for c in mcp_configs if c.name in allowed]

    if not mcp_configs:
        logger.debug("No MCP configurations matched allowmcps filter")
        return MCPToolkit([])

    # Create and connect clients
    clients = await create_mcp_clients(mcp_configs, connect=True, skip_errors=True)

    # Wrap in toolkit and initialize (list tools from each server)
    toolkit = MCPToolkit(clients)
    await toolkit.initialize()

    logger.info(
        f"MCP toolkit loaded: {len(clients)} servers, "
        f"{len(toolkit.list_tools())} tools"
    )

    return toolkit


class _ConfiguredToolProvider(IToolProvider):
    """Filter tool listings based on config while honoring explicit injections."""

    def __init__(
        self,
        *,
        manager: IToolManager,
        config: Config,
        explicit_names: set[str],
    ) -> None:
        self._manager = manager
        self._config = config
        self._explicit_names = explicit_names

    def list_tools(self) -> list[ITool]:
        tools = self._manager.load_tools(config=self._config)
        return [tool for tool in tools if self._is_enabled_name(tool.name)]

    def list_tool_defs(self) -> list[dict[str, Any]]:  # type: ignore[override]
        tool_defs = self._manager.list_tool_defs()
        filtered: list[dict[str, Any]] = []
        for tool_def in tool_defs:
            name = None
            metadata = tool_def.get("metadata")
            if isinstance(metadata, dict):
                name = metadata.get("display_name")
            if name is None or self._is_enabled_name(str(name)):
                filtered.append(tool_def)
        return filtered

    def _is_enabled_name(self, name: str) -> bool:
        if name in self._explicit_names:
            return True
        return self._config.is_component_enabled_name(ComponentType.TOOL, name)
