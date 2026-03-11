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
from dare_framework.config.action_handler import ConfigActionHandler
from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.types import Config
from dare_framework.context import Budget, Context, IAssembleContext, SmartContext
from dare_framework.event import DefaultEventLog
from dare_framework.event.kernel import IEventLog
from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.kernel import IHook
from dare_framework.hook._internal.agent_event_transport_hook import AgentEventTransportHook
from dare_framework.infra.component import ComponentType
from dare_framework.knowledge import IKnowledge, create_knowledge
from dare_framework.knowledge._internal.knowledge_tools import (
    KnowledgeAddTool,
    KnowledgeGetTool,
)
from dare_framework.mcp.action_handler import McpActionHandler
from dare_framework.memory import ILongTermMemory, IShortTermMemory, create_long_term_memory
from dare_framework.model.action_handler import ModelActionHandler
from dare_framework.model.default_model_adapter_manager import DefaultModelAdapterManager
from dare_framework.model.factories import (
    create_default_prompt_store,
)
from dare_framework.model.interfaces import IModelAdapterManager, IPromptStore
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import Prompt
from dare_framework.observability._internal.llm_io_capture_hook import (
    LLMIOCaptureHook,
    create_default_llm_io_capture_hook,
)
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.plan import Envelope
from dare_framework.plan._internal.composite_validator import CompositeValidator
from dare_framework.plan.interfaces import (
    IPlanner,
    IPlannerManager,
    IRemediator,
    IRemediatorManager,
    IStepExecutor,
    IValidator,
    IValidatorManager,
)
from dare_framework.security import ISecurityBoundary, NoOpSecurityBoundary, PolicySecurityBoundary
from dare_framework.skill import Skill, ISkillLoader, ISkillStore, SkillStoreBuilder
from dare_framework.skill._internal.action_handler import SkillsActionHandler
from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader
from dare_framework.tool import ToolResult, CapabilityDescriptor
from dare_framework.tool._internal.tools.ask_user import AskUserTool, IUserInputHandler
from dare_framework.tool.action_handler import ApprovalsActionHandler, ToolsActionHandler
from dare_framework.tool._internal.control.approval_manager import ToolApprovalManager
from dare_framework.tool.interfaces import IExecutionControl
from dare_framework.tool.kernel import ITool, IToolGateway, IToolManager, IToolProvider
from dare_framework.tool.tool_gateway import ToolGateway
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.tool.types import RunContext
from dare_framework.transport.interaction.control_handler import AgentControlHandler
from dare_framework.transport.interaction.dispatcher import ActionHandlerDispatcher
from dare_framework.transport.kernel import AgentChannel
from dare_framework.context.manage_context import ManageContextTool, MANAGE_CONTEXT_TOOL_NAME
from dare_framework.guidance import GuidanceQueue
from dare_framework.guidance.action_handler import GuidanceActionHandler

logger = logging.getLogger(__name__)

TBuilder = TypeVar("TBuilder", bound="_BaseAgentBuilder[Any]")
TAgent = TypeVar("TAgent", bound=BaseAgent)


class _BaseAgentBuilder(Generic[TAgent]):
    """Internal base builder shared by all public builder variants."""

    def __init__(self, name: str) -> None:
        self._name = name

        # Shared configuration surface (used by all builder variants).
        self._config: Config | None = None
        # 可选：上下文策略名称（如 "basic" / "smart"），由具体 Builder 解释含义。
        self._context_strategy: str | None = None
        # 可选：上下文压缩策略（如 "moving" / None），由 Context 解释含义。
        self._compression_strategy: str | None = None
        self._config_provider: IConfigProvider | None = None
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
        # Optional: per-context LLM上下文窗口大小（用于压缩），单位 token。
        # 仅作为 compression.max_context_tokens 的默认值挂载到 Context 上，
        # 不参与 Budget.max_tokens 计费语义。
        self._context_window_tokens: int | None = None
        # Tool wiring (shared across variants).
        self._tools: list[ITool] = []
        self._tool_providers: list[IToolProvider] = []
        self._tool_manager: IToolManager | None = None
        self._approval_manager: ToolApprovalManager | None = None

        # MCP tool provider (optional, provides MCP-backed tools).
        self._mcp_toolkit: IToolProvider | None = None
        self._mcp_manager: Any | None = None

        # Optional plan provider (e.g. plan_v2.Planner). When set, registered as tool provider
        # so the agent gets plan tools (create_plan, validate_plan, etc.). ReactAgentBuilder
        # also passes it to the agent so you can access agent.plan_provider (e.g. .state for copy_for_execution).
        self._plan_provider: IToolProvider | None = None

        # Optional transport channel (agent-facing).
        self._agent_channel: AgentChannel | None = None

        # User input handler for the built-in ask_user tool.
        self._user_input_handler: IUserInputHandler | None = None

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

    def with_config_provider(self: TBuilder, provider: IConfigProvider) -> TBuilder:
        """Inject config provider used when explicit config is not provided."""
        self._config_provider = provider
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

    def with_context_window_tokens(self: TBuilder, max_tokens: int | None) -> TBuilder:
        """配置单次请求的上下文窗口大小（用于压缩），单位 token。

        - 仅作为 Context 上的 context_window_tokens 挂载给 MovingCompressor 使用；
        - 不影响 Budget.max_tokens，后者只用于累计花销控制。
        """
        if max_tokens is None or max_tokens <= 0:
            self._context_window_tokens = None
        else:
            self._context_window_tokens = int(max_tokens)
        return self

    def with_context_strategy(self: TBuilder, strategy: str) -> TBuilder:
        """指定上下文策略名称，由具体 AgentBuilder 决定如何映射到具体 Context 实现。

        约定：
        - ReactAgentBuilder:
          - "basic" -> 使用基础 Context，不自动挂载 manage_context。
          - "smart"（默认）-> 使用 SmartContext，并自动挂载 manage_context。
        - 其它 Builder 可以按需扩展或忽略该字段。
        """
        self._context_strategy = strategy.strip() or None
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

    def with_tool_gateway(self: TBuilder, gateway: IToolManager) -> TBuilder:
        self._tool_manager = gateway
        return self

    def with_approval_manager(self: TBuilder, approval_manager: ToolApprovalManager) -> TBuilder:
        """Inject tool approval manager used for approval-required invocations."""
        self._approval_manager = approval_manager
        return self

    def add_tool_provider(self: TBuilder, provider: IToolProvider) -> TBuilder:
        self._tool_providers.append(provider)
        return self

    def with_plan_provider(self: TBuilder, plan_provider: IToolProvider) -> TBuilder:
        """Optionally mount a plan provider (e.g. plan_v2.Planner). Its tools are registered;
        for ReactAgent, the same provider is exposed as agent.plan_provider (e.g. to read .state)."""
        self._plan_provider = plan_provider
        return self

    def with_user_input_handler(self: TBuilder, handler: IUserInputHandler) -> TBuilder:
        """Inject a custom user-input handler for the built-in ``ask_user`` tool.

        If not called, the default ``CLIUserInputHandler`` (stdin/stdout) is
        used.  Pass a custom implementation for web UIs, Slack bots, etc.
        """
        self._user_input_handler = handler
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
        """Build agent with shared dependency resolution and optional MCP preload."""
        config = self._resolve_config()
        if config is not None and getattr(config, "mcp_paths", None):
            from dare_framework.mcp.manager import MCPManager

            self._mcp_manager = MCPManager(config)
            self._mcp_toolkit = await self._mcp_manager.load_provider()
        else:
            self._mcp_manager = None
            self._mcp_toolkit = None
        model, model_manager = self._resolve_model_and_model_manager(config)
        # 记录最终解析出的 model，便于子类在构建 Context 时使用（例如为 MovingCompressor 注入 LLM）。
        self._model = model
        approval_manager = self._resolve_approval_manager(config)
        sys_prompt = self._resolve_sys_prompt(model)
        knowledge = self._resolved_knowledge()
        skill_store = self._resolve_skill_store(config) if self._enable_skill_tool else None
        tools = self._resolve_tools(knowledge, skill_store)
        tool_gateway, tool_manager = self._resolve_tool_gateway_and_tool_manager(
            config,
            tools,
            self._tool_providers,
        )
        guidance_queue = GuidanceQueue()
        context = self._build_context(
            config=config,
            knowledge=knowledge,
            sys_prompt=sys_prompt,
            tool_gateway=tool_gateway,
            guidance_queue=guidance_queue,
        )
        self._context = context
        agent = self._build_impl(
            config=config,
            model=model,
            context=context,
            tool_gateway=tool_gateway,
            approval_manager=approval_manager,
            agent_channel=self._agent_channel,
        )
        if self._agent_channel is not None:
            control_handler = AgentControlHandler(agent)
            action_dispatcher = ActionHandlerDispatcher(logger=logger)
            action_dispatcher.register_action_handler(
                ConfigActionHandler(config=config, manager=self._config_provider)
            )
            action_dispatcher.register_action_handler(
                McpActionHandler(config=config, manager=self._config_provider)
            )
            action_dispatcher.register_action_handler(ToolsActionHandler(tool_manager))
            action_dispatcher.register_action_handler(ApprovalsActionHandler(approval_manager))
            action_dispatcher.register_action_handler(GuidanceActionHandler(guidance_queue))
            if skill_store is not None:
                action_dispatcher.register_action_handler(SkillsActionHandler(skill_store))
            action_dispatcher.register_action_handler(
                ModelActionHandler(agent, config, model_manager)
            )
            self._agent_channel.add_action_handler_dispatcher(action_dispatcher)
            self._agent_channel.add_agent_control_handler(control_handler)
        return agent

    def _build_impl(
            self,
            *,
            config: Config,
            model: IModelAdapter,
            context: Context,
            tool_gateway: IToolGateway,
            approval_manager: ToolApprovalManager,
            agent_channel: AgentChannel | None,
    ) -> TAgent:
        """Override in subclasses to perform the actual build. Called by build() after MCP load."""
        raise NotImplementedError

    def _resolved_long_term_memory(self) -> ILongTermMemory | None:
        """LTM from explicit with_long_term_memory() or from config.long_term_memory + embedding_adapter."""
        if self._long_term_memory is not None:
            return self._long_term_memory
        config = self._resolve_config()
        if not config.long_term_memory:
            return None
        return create_long_term_memory(config.long_term_memory, self._embedding_adapter)

    def _resolved_knowledge(self) -> IKnowledge | None:
        """Knowledge from explicit with_knowledge() or from config.knowledge + embedding_adapter."""
        if self._knowledge is not None:
            return self._knowledge
        config = self._resolve_config()
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

    def _resolve_config(self) -> Config:
        if self._config is not None:
            return self._config
        if self._config_provider is not None:
            # Freeze one snapshot so all components in this build share a single config view.
            self._config = self._config_provider.current()
            return self._config
        # Ensure all components built in this pass share the same Config instance.
        self._config = Config()
        return self._config

    def _resolve_prompt_store(self) -> IPromptStore:
        if self._prompt_store is not None:
            return self._prompt_store
        return create_default_prompt_store(self._resolve_config())

    def _resolve_sys_prompt(self, model: IModelAdapter) -> Prompt | None:
        prompt = None
        prompt_id = None
        if self._sys_prompt is not None:
            prompt = self._sys_prompt[1]
            prompt_id = self._sys_prompt[0]
        if prompt is not None:
            return prompt
        if prompt_id is None:
            prompt_id = self._resolve_config().default_prompt_id
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

    def _resolve_tool_gateway_and_tool_manager(
            self,
            config: Config,
            tools: list[ITool],
            tool_providers: list[IToolProvider],
    ) -> tuple[IToolGateway, IToolManager]:
        """Resolve tool manager and always wrap invocation behind ToolGateway."""
        if self._tool_manager is not None:
            tool_manager = self._tool_manager
        else:
            tool_manager = ToolManager(config=config)
            self._tool_manager = tool_manager

        providers = list(tool_providers)
        if self._plan_provider is not None and self._plan_provider not in providers:
            providers.append(self._plan_provider)
        if self._mcp_toolkit is not None and self._mcp_toolkit not in providers:
            providers.append(self._mcp_toolkit)

        for provider in providers:
            tool_manager.register_provider(provider)
        for tool in tools:
            tool_manager.register_tool(tool)

        # Apply config-level component disables to all registered tools except the ones
        # explicitly injected via the builder (those must remain available).
        disabled = set(config.component_settings(ComponentType.TOOL).disabled)
        explicit_names = {tool.name for tool in tools}
        for tool_name in disabled:
            if tool_name in explicit_names:
                continue
            try:
                tool_manager.change_capability_status(tool_name, enabled=False)
            except KeyError:
                # Config may reference tools that are not registered in this build.
                continue
        return ToolGateway(tool_manager), tool_manager

    def _resolve_approval_manager(self, config: Config) -> ToolApprovalManager:
        if self._approval_manager is not None:
            return self._approval_manager
        manager = ToolApprovalManager.from_paths(
            workspace_dir=config.workspace_dir,
            user_dir=config.user_dir,
        )
        self._approval_manager = manager
        return manager

    def _resolve_model_and_model_manager(self, config: Config) -> tuple[IModelAdapter, IModelAdapterManager]:
        manager = self._model_adapter_manager or DefaultModelAdapterManager(config=config)
        if self._model is not None:
            return self._model, manager
        model = manager.load_model_adapter(config=config)
        if model is None:
            raise ValueError("Model adapter manager did not return an IModelAdapter")
        return model, manager

    def _resolve_tools(self, knowledge: IKnowledge | None, skill_store: ISkillStore | None) -> list[
        ITool]:
        """Resolve explicit tools (local + skill + knowledge) for registration."""
        explicit = list(self._tools)
        explicit_names = {tool.name for tool in explicit}
        skill_tool = None
        if skill_store is not None:
            from dare_framework.skill.defaults import SearchSkillTool
            skill_tool = SearchSkillTool(skill_store)
        if skill_tool is not None and skill_tool.name not in explicit_names:
            explicit.append(skill_tool)
            explicit_names.add(skill_tool.name)
        if knowledge is not None:
            explicit.append(KnowledgeGetTool(knowledge))
            explicit.append(KnowledgeAddTool(knowledge))
        # Built-in ask_user tool — always available so the LLM can request user input.
        ask_user_tool = AskUserTool(handler=self._user_input_handler)
        if ask_user_tool.name not in explicit_names:
            explicit.append(ask_user_tool)
        return explicit

    def _context_class(self) -> type[Context]:
        """Override in ReactAgentBuilder to use SmartContext (update_core, task_complete, etc.)."""
        return Context

    def _build_context(
            self,
            *,
            config: Config,
            knowledge: IKnowledge | None,
            sys_prompt: Prompt | None,
            tool_gateway: IToolGateway | None,
            guidance_queue: GuidanceQueue | None = None,
    ) -> Context:
        """Build context with shared defaults for all builder variants.

        若上下文 compression 策略为 "moving" 且已解析出 model，则为 Context 挂载带 model 的 MovingCompressor（一次性注入 LLM）。
        这样所有基于 Context 的 Agent（SimpleChat/React/Dare）都具备统一的「moving 压缩」能力，同时可以通过 compression 参数化关闭或更换策略。
        """
        sys_skill = None if self._enable_skill_tool else self._sys_skill
        context = self._context_class()(
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
            context_window_tokens=self._context_window_tokens,
            guidance_queue=guidance_queue,
        )
        # 若 builder 已解析到 model：
        # - 默认（compression 为空或其他值）视为启用 "moving" 压缩；
        # - 显式配置 compression="no_compress" 时不挂载 MovingCompressor。
        normalized_compression = (self._compression_strategy or "moving").strip().lower()
        if self._model is not None and normalized_compression == "moving":
            from dare_framework.compression import MovingCompressor
            context.set_moving_compressor(MovingCompressor(model=self._model))
        return context

class SimpleChatAgentBuilder(_BaseAgentBuilder[SimpleChatAgent]):
    """Builder for SimpleChatAgent."""

    def _build_impl(
            self,
            *,
            config: Config,
            model: IModelAdapter,
            context: Context,
            tool_gateway: IToolGateway,
            approval_manager: ToolApprovalManager,
            agent_channel: AgentChannel | None,
    ) -> SimpleChatAgent:
        _ = (config, approval_manager)
        return SimpleChatAgent(
            name=self._name,
            model=model,
            context=context,
            tool_gateway=tool_gateway,
            agent_channel=agent_channel,
        )


class ReactAgentBuilder(_BaseAgentBuilder[ReactAgent]):
    """Builder for ReactAgent (ReAct tool loop).

    Optional plan: use with_plan_provider(plan_v2.Planner(state)) to mount plan tools;
    the agent then exposes agent.plan_provider (e.g. .state for copy_for_execution).
    Uses SmartContext (update_core, task_complete, stm_remove_by_ids).
    """

    def _context_class(self) -> type[Context]:
        """根据上下文策略选择 Context 实现。

        - 默认 / 未设置 -> 基础 Context（pure ReAct）。
        - strategy == "smart" -> SmartContext（启用 CORE / task_complete / manage_context 能力）。
        - 其它策略名称目前等价于默认（基础 Context），预留扩展点。
        """
        strategy = (getattr(self, "_context_strategy", None) or "").strip().lower()
        if strategy == "smart":
            return SmartContext
        return Context

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._max_tool_rounds: int = 10

    def with_max_tool_rounds(self: "ReactAgentBuilder", max_rounds: int) -> "ReactAgentBuilder":
        """Set max ReAct tool loop rounds. Plan agents may need more (e.g. 25) for multi-step delegation."""
        self._max_tool_rounds = max_rounds
        return self

    def _resolve_tools(self, knowledge: IKnowledge | None, skill_store: ISkillStore | None) -> list[ITool]:
        """在基类工具集合基础上，为 ReactAgent 自动挂载 manage_context（仅 smart 策略下）。

        - 默认 / 非 "smart" 策略：不自动挂 manage_context，保持纯 ReAct 行为。
        - strategy == "smart"：若尚未存在同名工具，则自动追加 ManageContextTool。
        """
        tools = super()._resolve_tools(knowledge, skill_store)
        strategy = (getattr(self, "_context_strategy", None) or "").strip().lower()
        if strategy != "smart":
            return tools

        if not any(getattr(t, "name", "") == MANAGE_CONTEXT_TOOL_NAME for t in tools):
            tools.append(ManageContextTool())
        return tools

    def _build_impl(
            self,
            *,
            config: Config,
            model: IModelAdapter,
            context: SmartContext,
            tool_gateway: IToolGateway,
            approval_manager: ToolApprovalManager,
            agent_channel: AgentChannel | None,
    ) -> ReactAgent:
        _ = (config, approval_manager)
        return ReactAgent(
            name=self._name,
            model=model,
            context=context,
            tool_gateway=tool_gateway,
            plan_provider=self._plan_provider,
            agent_channel=agent_channel,
            max_tool_rounds=self._max_tool_rounds,
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
        self._execution_mode: str = "model_driven"
        self._step_executor: IStepExecutor | None = None
        self._security_boundary: ISecurityBoundary | None = None
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

    def with_execution_mode(self, execution_mode: str) -> DareAgentBuilder:
        normalized = execution_mode.strip().lower()
        if normalized not in {"model_driven", "step_driven"}:
            raise ValueError("execution_mode must be 'model_driven' or 'step_driven'")
        self._execution_mode = normalized
        return self

    def with_step_executor(self, step_executor: IStepExecutor) -> DareAgentBuilder:
        self._step_executor = step_executor
        return self

    def add_hooks(self, *hooks: IHook) -> DareAgentBuilder:
        self._hooks.extend(hooks)
        return self

    def with_telemetry(self, telemetry: ITelemetryProvider) -> DareAgentBuilder:
        self._telemetry = telemetry
        return self

    def with_security_boundary(self, security_boundary: ISecurityBoundary) -> DareAgentBuilder:
        """Inject an explicit security boundary for tool preflight."""
        self._security_boundary = security_boundary
        return self

    def with_verbose(self, verbose: bool = True) -> DareAgentBuilder:
        self._verbose = verbose
        return self

    def _build_impl(
            self,
            *,
            config: Config,
            model: IModelAdapter,
            context: Context,
            tool_gateway: IToolGateway,
            approval_manager: ToolApprovalManager,
            agent_channel: AgentChannel | None,
    ) -> DareAgent:
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
        auto_capture_hook = create_default_llm_io_capture_hook(config)
        if auto_capture_hook is not None:
            if not any(isinstance(hook, LLMIOCaptureHook) for hook in explicit_hooks):
                explicit_hooks.append(auto_capture_hook)
        config_hooks: list[IHook] = []
        manager = self._hook_manager
        if manager is not None:
            discovered = manager.load_hooks(config=self._manager_config())
            config_hooks = [hook for hook in discovered if config.is_component_enabled(hook)]

        system_hooks: list[IHook] = []
        if agent_channel is not None:
            existing = {hook.name for hook in [*config_hooks, *explicit_hooks]}
            if "agent_event_transport" not in existing:
                system_hooks.append(AgentEventTransportHook(agent_channel))

        source_rank = {"system": 0, "config": 1, "code": 2}
        ordered_candidates: list[tuple[int, int, int, IHook]] = []
        registration_order = 0
        for source, hooks_group in (
            ("system", system_hooks),
            ("config", config_hooks),
            ("code", explicit_hooks),
        ):
            for hook in hooks_group:
                registration_order += 1
                ordered_candidates.append(
                    (
                        source_rank[source],
                        config.hooks.priority_for(hook.name),
                        registration_order,
                        hook,
                    )
                )

        hooks = []
        seen_names: set[str] = set()
        for _, _, _, hook in sorted(ordered_candidates, key=lambda item: (item[0], item[1], item[2])):
            if hook.name in seen_names:
                continue
            seen_names.add(hook.name)
            hooks.append(hook)
        if not hooks:
            hooks = None

        telemetry = self._telemetry
        security_boundary = self._resolve_security_boundary(config)
        event_log = self._resolve_event_log(config)
        return DareAgent(
            name=self._name,
            model=model,
            context=context,
            tool_gateway=tool_gateway,
            mcp_manager=self._mcp_manager,
            execution_control=self._execution_control,
            planner=planner,
            validator=validator,
            remediator=remediator,
            event_log=event_log,
            hooks=hooks,
            telemetry=telemetry,
            security_boundary=security_boundary,
            step_executor=self._step_executor,
            execution_mode=self._execution_mode,
            agent_channel=agent_channel,
            verbose=self._verbose,
            approval_manager=approval_manager,
        )

    def _resolve_event_log(self, config: Config) -> IEventLog | None:
        if self._event_log is not None:
            return self._event_log
        if not config.event_log.enabled:
            return None

        # Normalize blank templated values (e.g. empty env var expansion) to
        # "unset" so event log keeps the documented default db location.
        db_path = config.event_log.path
        if db_path is None or not str(db_path).strip():
            db_path = str(Path(config.workspace_dir) / ".dare" / "events.db")
        return DefaultEventLog(db_path)

    def _resolve_security_boundary(self, config: Config) -> ISecurityBoundary:
        if self._security_boundary is not None:
            return self._security_boundary
        # Treat null/empty config as "unset" so templated values do not
        # silently disable security by coercing None -> "none".
        raw_mode = config.security.get("boundary")
        if raw_mode is None:
            raw_mode = config.security.get("mode")
        if raw_mode is None:
            raw_mode = "policy"
        mode = str(raw_mode).strip().lower() or "policy"
        if mode in {"off", "none", "noop", "disabled"}:
            boundary: ISecurityBoundary = NoOpSecurityBoundary()
        else:
            boundary = PolicySecurityBoundary.from_config(config.security)
        self._security_boundary = boundary
        return boundary


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
    if config is None:
        raise ValueError("load_mcp_toolkit requires a non-null Config.")
    from dare_framework.mcp.manager import MCPManager

    manager = MCPManager(config)
    return await manager.load_provider(paths=paths)
