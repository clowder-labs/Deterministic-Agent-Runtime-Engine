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
from typing import Any, Generic, TypeVar

from dare_framework.agent.base_agent import BaseAgent
from dare_framework.agent.dare_agent import DareAgent
from dare_framework.agent.react_agent import ReactAgent
from dare_framework.agent.simple_chat import SimpleChatAgent
from dare_framework.config.types import Config
from dare_framework.context import Budget, Context, IAssembleContext
from dare_framework.event.kernel import IEventLog
from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.kernel import IHook
from dare_framework.knowledge import IKnowledge, create_knowledge
from dare_framework.knowledge._internal.knowledge_tools import (
    KnowledgeAddTool,
    KnowledgeGetTool,
)
from dare_framework.memory import ILongTermMemory, IShortTermMemory, create_long_term_memory
from dare_framework.model.factories import (
    create_default_model_adapter_manager,
    create_default_prompt_store,
)
from dare_framework.model.interfaces import IModelAdapterManager, IPromptStore
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import Prompt
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.plan._internal.composite_validator import CompositeValidator
from dare_framework.plan.interfaces import (
    IPlanner,
    IPlannerManager,
    IRemediator,
    IRemediatorManager,
    IValidator,
    IValidatorManager,
)
from dare_framework.skill import Skill, ISkillLoader, ISkillStore, SkillStoreBuilder
from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader
from dare_framework.tool.interfaces import IExecutionControl
from dare_framework.tool.kernel import ITool, IToolGateway, IToolManager, IToolProvider
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.tool.types import RunContext
from dare_framework.transport.kernel import AgentChannel

logger = logging.getLogger(__name__)

TBuilder = TypeVar("TBuilder", bound="_BaseAgentBuilder[Any]")
TAgent = TypeVar("TAgent", bound=BaseAgent)


class _BaseAgentBuilder(Generic[TAgent]):
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
        self._assemble_context: IAssembleContext | None = None
        self._budget: Budget | None = None
        self._short_term_memory: IShortTermMemory | None = None
        self._long_term_memory: ILongTermMemory | None = None
        self._knowledge: IKnowledge | None = None
        self._embedding_adapter: Any = None
        """Optional; used with config.knowledge to create vector knowledge from config."""
        self._prompt_store: IPromptStore | None = None
        self._sys_prompt: tuple[str | None, Prompt | None] | None = None
        # Tool wiring (shared across variants).
        self._tools: list[ITool] = []
        self._tool_providers: list[IToolProvider] = []
        self._tool_gateway: IToolGateway | None = None

        # MCP tool provider (optional, provides MCP-backed tools).
        self._mcp_toolkit: IToolProvider | None = None

        # Optional transport channel (agent-facing).
        self._agent_channel: AgentChannel | None = None

        self._sys_skill: Skill | None = None
        self._enable_skill_tool: bool = True
        self._skill_loaders: list[ISkillLoader] = []
        self._skill_store: ISkillStore | None = None
        self._disabled_skill_ids: set[str] = set()

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
        self._sys_prompt = (None, prompt)
        return self

    def with_prompt_id(self: TBuilder, prompt_id: str) -> TBuilder:
        self._sys_prompt = (prompt_id, None)
        return self

    def with_context(self: TBuilder, assemble_context: IAssembleContext) -> TBuilder:
        self._assemble_context = assemble_context
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

    def with_embedding_adapter(self: TBuilder, adapter: Any) -> TBuilder:
        """Inject embedding adapter for config-driven vector knowledge.

        When config.knowledge is set and type is \"vector\", create_knowledge uses
        this adapter. Ignored if with_knowledge() was already called.
        """
        self._embedding_adapter = adapter
        return self

    def add_tools(self: TBuilder, *tools: ITool) -> TBuilder:
        self._tools.extend(tools)
        return self

    def with_tool_gateway(self: TBuilder, gateway: IToolGateway) -> TBuilder:
        self._tool_gateway = gateway
        return self

    def add_tool_provider(self: TBuilder, provider: IToolProvider) -> TBuilder:
        self._tool_providers.append(provider)
        return self

    def with_agent_channel(self: TBuilder, channel: AgentChannel) -> TBuilder:
        """Attach an AgentChannel for transport-backed output/hook streaming."""
        self._agent_channel = channel
        return self

    def with_sys_skill(self: TBuilder, skill: Skill | None) -> TBuilder:
        """Set explicit sys_skill for prompt enrichment mode."""
        self._sys_skill = skill
        return self

    def with_skill_tool(self: TBuilder, enable_skill_tool: bool) -> TBuilder:
        """Toggle automatic registration of search_skill tool."""
        self._enable_skill_tool = enable_skill_tool
        return self

    def with_skill_store(self: TBuilder, skill_store: ISkillStore) -> TBuilder:
        """Inject a pre-built skill store."""
        self._skill_store = skill_store
        return self

    def add_skill_loader(self: TBuilder, skill_loader: ISkillLoader) -> TBuilder:
        """Append an external skill loader for store composition."""
        self._skill_loaders.append(skill_loader)
        return self

    def disable_skills(self: TBuilder, *skill_ids: str) -> TBuilder:
        """Disable skills by id from the builder-composed store."""
        for skill_id in skill_ids:
            normalized = skill_id.strip()
            if normalized:
                self._disabled_skill_ids.add(normalized)
        return self

    def with_skill_paths(self: TBuilder, *paths: str | Path) -> TBuilder:
        """Backward-compatible helper that appends filesystem loaders for paths."""
        for path in paths:
            self._skill_loaders.append(FileSystemSkillLoader(Path(path)))
        return self

    async def build(self) -> TAgent:
        """Build the agent. When with_config() was used and config.mcp_paths is set, loads MCP inside build()."""
        if self._config is not None and getattr(self._config, "mcp_paths", None):
            self._mcp_toolkit = await load_mcp_toolkit(self._config)
        return self._build_impl()

    def _build_impl(self) -> TAgent:
        """Override in subclasses to perform the actual build. Called by build() after MCP load."""
        raise NotImplementedError

    def _resolved_long_term_memory(self) -> ILongTermMemory | None:
        """LTM from explicit with_long_term_memory() or from config.long_term_memory + embedding_adapter."""
        if self._long_term_memory is not None:
            return self._long_term_memory
        config = self._effective_config()
        if not config.long_term_memory:
            return None
        return create_long_term_memory(config.long_term_memory, self._embedding_adapter)

    def _resolved_knowledge(self) -> IKnowledge | None:
        """Knowledge from explicit with_knowledge() or from config.knowledge + embedding_adapter."""
        if self._knowledge is not None:
            return self._knowledge
        config = self._effective_config()
        if not config.knowledge:
            return None
        return create_knowledge(config.knowledge, self._embedding_adapter)

    def _default_run_context(self) -> RunContext[Any]:
        """Create a default run context for tool invocation."""
        return RunContext(deps=None, metadata={"agent": self._name})

    def _resolve_skill_store(self, config: Config) -> ISkillStore:
        if self._skill_store is not None:
            return self._skill_store

        builder = SkillStoreBuilder.config(config)
        for skill_loader in self._skill_loaders:
            builder.with_skill_loader(skill_loader)
        for skill_id in sorted(self._disabled_skill_ids):
            builder.disable_skill(skill_id)
        return builder.build()

    def _effective_config(self) -> Config:
        if self._config is None:
            # Ensure all components built in this pass share the same Config instance.
            self._config = Config()
        return self._config

    def _resolve_prompt_store(self) -> IPromptStore:
        if self._prompt_store is not None:
            return self._prompt_store
        return create_default_prompt_store(self._effective_config())

    def _resolve_sys_prompt(self, model: IModelAdapter) -> Prompt | None:
        prompt = None
        prompt_id = None
        if self._sys_prompt is not None:
            prompt = self._sys_prompt[1]
            prompt_id = self._sys_prompt[0]
        if prompt is not None:
            return prompt
        if prompt_id is None:
            prompt_id = self._effective_config().default_prompt_id
        if prompt_id is None:
            prompt_id = "base.system"

        model_name = getattr(model, "model", None) or getattr(model, "name", None)
        if not model_name:
            raise ValueError("Model adapter must define a stable name for prompt resolution")
        try:
            store = self._resolve_prompt_store()
            return store.get(prompt_id, model=model_name)
        except KeyError as exc:
            raise ValueError(f"Prompt not found: {prompt_id}") from exc

    def _ensure_tool_gateway(
            self,
            config: Config,
            tools: list[ITool],
            tool_providers: list[IToolProvider],
    ) -> IToolGateway | None:
        """Return a ToolGateway if tool wiring requires one."""
        if self._tool_gateway is not None:
            gateway = self._tool_gateway
        else:
            gateway = ToolManager(config=config)
            self._tool_gateway = gateway
        if not isinstance(gateway, IToolManager):
            return gateway

        providers = list(tool_providers)
        if self._mcp_toolkit is not None and self._mcp_toolkit not in providers:
            providers.append(self._mcp_toolkit)
        for provider in providers:
            gateway.register_provider(provider)
        for tool in tools:
            gateway.register_tool(tool)
        return gateway

    def _resolve_model(self, config: Config) -> IModelAdapter:
        if self._model is not None:
            return self._model
        manager = self._model_adapter_manager or create_default_model_adapter_manager(config)
        if manager is None:
            raise ValueError("Builder requires a model adapter (explicit or manager-resolved)")

        candidate = manager.load_model_adapter(config=config)
        if candidate is None:
            raise ValueError("Model adapter manager did not return an IModelAdapter")
        return candidate

    def _resolved_skill_search_tool(self, config: Config) -> ITool | None:
        if not self._enable_skill_tool:
            return None
        from dare_framework.skill.defaults import (
            SearchSkillTool,
        )
        return SearchSkillTool(self._resolve_skill_store(config))

    def _resolve_tools(self, config: Config, knowledge: IKnowledge | None) -> list[ITool]:
        """Resolve explicit tools (local + skill + knowledge) for registration."""
        explicit = list(self._tools)
        explicit_names = {tool.name for tool in explicit}
        skill_tool = self._resolved_skill_search_tool(config)

        if skill_tool is not None and skill_tool.name not in explicit_names:
            explicit.append(skill_tool)
            explicit_names.add(skill_tool.name)
        if knowledge is not None:
            explicit.append(KnowledgeGetTool(knowledge))
            explicit.append(KnowledgeAddTool(knowledge))
        return explicit

    def _build_context(
            self,
            *,
            config: Config,
            knowledge: IKnowledge | None,
            sys_prompt: Prompt | None,
            tool_gateway: IToolGateway | None,
    ) -> Context:
        """Build context with shared defaults for all builder variants."""
        sys_skill = None if self._enable_skill_tool else self._sys_skill
        return Context(
            id=f"context_{self._name}",
            short_term_memory=self._short_term_memory,
            long_term_memory=self._resolved_long_term_memory(),
            knowledge=knowledge,
            budget=self._budget or Budget(),
            sys_prompt=sys_prompt,
            skill=sys_skill,
            config=config,
            tool_gateway=tool_gateway,
            assemble_context=self._assemble_context,
        )


class SimpleChatAgentBuilder(_BaseAgentBuilder[SimpleChatAgent]):
    """Builder for SimpleChatAgent."""

    def _build_impl(self) -> SimpleChatAgent:
        config = self._effective_config()
        model = self._resolve_model(config)
        sys_prompt = self._resolve_sys_prompt(model)
        knowledge = self._resolved_knowledge()
        tools = self._resolve_tools(config, knowledge)
        tool_gateway = self._ensure_tool_gateway(config, tools, self._tool_providers)
        context = self._build_context(config=config, knowledge=knowledge, sys_prompt=sys_prompt,
                                      tool_gateway=tool_gateway)
        self._context = context
        return SimpleChatAgent(
            name=self._name,
            model=model,
            context=self._context,
            agent_channel=self._agent_channel,
        )


class ReactAgentBuilder(_BaseAgentBuilder[ReactAgent]):
    """Builder for ReactAgent (ReAct tool loop)."""

    def _build_impl(self) -> ReactAgent:
        config = self._effective_config()
        model = self._resolve_model(config)
        sys_prompt = self._resolve_sys_prompt(model)
        knowledge = self._resolved_knowledge()
        tools = self._resolve_tools(config, knowledge)
        tool_gateway = self._ensure_tool_gateway(config, tools, self._tool_providers)
        context = self._build_context(config=config, knowledge=knowledge, sys_prompt=sys_prompt,
                                      tool_gateway=tool_gateway)
        self._context = context

        return ReactAgent(
            name=self._name,
            model=model,
            context=self._context,
            agent_channel=self._agent_channel,
        )


class DareAgentBuilder(_BaseAgentBuilder[DareAgent]):
    """Builder for DareAgent (five-layer orchestration)."""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self._planner: IPlanner | None = None
        self._validators: list[IValidator] = []
        self._remediator: IRemediator | None = None

        self._event_log: IEventLog | None = None
        self._execution_control: IExecutionControl | None = None
        self._hooks: list[IHook] = []
        self._telemetry: ITelemetryProvider | None = None
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

    def with_telemetry(self, telemetry: ITelemetryProvider) -> DareAgentBuilder:
        self._telemetry = telemetry
        return self

    def with_verbose(self, verbose: bool = True) -> DareAgentBuilder:
        self._verbose = verbose
        return self

    def _build_impl(self) -> DareAgent:
        config = self._effective_config()
        model = self._resolve_model(config)
        sys_prompt = self._resolve_sys_prompt(model)
        knowledge = self._resolved_knowledge()
        tools = self._resolve_tools(config, knowledge)
        tool_gateway = self._ensure_tool_gateway(config, tools, self._tool_providers)
        context = self._build_context(config=config, knowledge=knowledge, sys_prompt=sys_prompt,
                                      tool_gateway=tool_gateway)
        planner = self._planner
        if planner is None:
            manager = self._planner_manager
            if manager is not None:
                planner = manager.load_planner(config=config)

        validators = list(self._validators)
        manager = self._validator_manager
        if manager is not None:
            discovered = manager.load_validators(config=config)
            validators.extend([v for v in discovered if self._config is None or self._config.is_component_enabled(v)])

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

        telemetry = self._telemetry

        self._context = context

        return DareAgent(
            name=self._name,
            model=model,
            context=context,
            tool_gateway=tool_gateway,
            execution_control=self._execution_control,
            planner=planner,
            validator=validator,
            remediator=remediator,
            event_log=self._event_log,
            hooks=hooks,
            telemetry=telemetry,
            agent_channel=self._agent_channel,
            verbose=self._verbose,
        )


__all__ = ["DareAgentBuilder", "ReactAgentBuilder", "SimpleChatAgentBuilder"]


async def load_mcp_toolkit(
        config: Config,
        *,
        paths: list[str | Path] | None = None,
) -> IToolProvider:
    """Load and initialize an MCP tool provider from configuration.

    Scans configured directories for MCP server definitions, creates clients,
    connects to servers, and returns an initialized MCPToolProvider.

    Args:
        config: Configuration with mcp_paths and allow_mcps settings.
                Must be non-null.
        paths: Explicit list of paths to scan. Overrides config.mcp_paths.

    Returns:
        Initialized MCPToolProvider (implements IToolProvider).

    Example (called internally by builder.build() when config.mcp_paths is set):
        config = Config(mcp_paths=[".dare/mcp"], ...)
        builder = DareAgentBuilder("my_agent").with_config(config)
        agent = await builder.build()

    Note:
        Remember to close the provider when done to disconnect MCP clients:
            await provider.close()
    """
    from dare_framework.mcp.defaults import create_mcp_clients, load_mcp_configs, MCPToolProvider
    if config is None:
        raise ValueError("load_mcp_toolkit requires a non-null Config.")

    # Determine scan paths
    if paths is None:
        paths = config.mcp_paths if config.mcp_paths else None

    # todo 这后面的内容都可以放到mcp manager的位置去搞定的 然后还有重新加载某个mcp或者全部mcp mcp的管理应该都放到那边的
    # Load MCP server configurations
    mcp_configs = load_mcp_configs(
        paths=paths,
        workspace_dir=config.workspace_dir,
        user_dir=config.user_dir,
    )

    if not mcp_configs:
        logger.debug("No MCP configurations found")
        return MCPToolProvider([])

    # Filter by allow_mcps if specified
    if config.allow_mcps:
        allowed = set(config.allow_mcps)
        mcp_configs = [c for c in mcp_configs if c.name in allowed]

    if not mcp_configs:
        logger.debug("No MCP configurations matched allow_mcps filter")
        return MCPToolProvider([])

    # Create and connect clients
    clients = await create_mcp_clients(mcp_configs, connect=True, skip_errors=True)

    # Wrap in provider and initialize (list tools from each server)
    provider = MCPToolProvider(clients)
    await provider.initialize()

    logger.info(
        f"MCP tool provider loaded: {len(clients)} servers, "
        f"{len(provider.list_tools())} tools"
    )

    return provider
