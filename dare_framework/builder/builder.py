"""Agent builders for composing agents deterministically.

This module provides two public builders:
- SimpleChatAgentBuilder: builds SimpleChatAgent (simple chat mode)
- FiveLayerAgentBuilder: builds FiveLayerAgent (five-layer orchestration)

All builder variants share the same precedence rules:
1) Explicit builder injection wins (highest precedence).
2) Missing components may be resolved via injected domain managers + Config.
3) Multi-load component categories use extend semantics.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, TypeVar

from dare_framework.agent import FiveLayerAgent, SimpleChatAgent
from dare_framework.config.types import Config
from dare_framework.context import Budget, Context
from dare_framework.event.kernel import IEventLog
from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.kernel import IHook
from dare_framework.knowledge import IKnowledge
from dare_framework.memory import ILongTermMemory, IShortTermMemory
from dare_framework.model.interfaces import IModelAdapter, IModelAdapterManager
from dare_framework.plan._internal.composite_validator import CompositeValidator
from dare_framework.plan.interfaces import (
    IPlanner,
    IPlannerManager,
    IRemediator,
    IRemediatorManager,
    IValidator,
    IValidatorManager,
)
from dare_framework.protocol_adapter_manager import IProtocolAdapterManager
from dare_framework.tool._internal.gateway.default_tool_gateway import DefaultToolGateway
from dare_framework.tool._internal.providers.gateway_tool_provider import GatewayToolProvider
from dare_framework.tool._internal.providers.native_tool_provider import NativeToolProvider
from dare_framework.tool.interfaces import ITool, IToolManager, IToolProvider, RunContext
from dare_framework.tool.kernel import IExecutionControl, IToolGateway

TBuilder = TypeVar("TBuilder", bound="_BaseAgentBuilder")


class _BaseAgentBuilder:
    """Internal base builder shared by all public builder variants."""

    def __init__(self, name: str) -> None:
        self._name = name

        # Shared configuration surface (used by all builder variants).
        self._config: Config | None = None
        self._tool_manager: IToolManager | None = None
        self._model_adapter_manager: IModelAdapterManager | None = None
        self._planner_manager: IPlannerManager | None = None
        self._validator_manager: IValidatorManager | None = None
        self._remediator_manager: IRemediatorManager | None = None
        self._protocol_adapter_manager: IProtocolAdapterManager | None = None
        self._hook_manager: IHookManager | None = None

        # Core components (commonly used across agent variants).
        self._model: IModelAdapter | None = None
        self._context: Context | None = None
        self._budget: Budget | None = None
        self._short_term_memory: IShortTermMemory | None = None
        self._long_term_memory: ILongTermMemory | None = None
        self._knowledge: IKnowledge | None = None

        # Tool wiring (shared across variants).
        self._tools: list[ITool] = []
        self._tool_gateway: IToolGateway | None = None
        self._tool_provider: IToolProvider | None = None
        self._run_context_factory: Callable[[], RunContext[Any]] = self._default_run_context

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
        tool_manager: IToolManager | None = None,
        model_adapter_manager: IModelAdapterManager | None = None,
        planner_manager: IPlannerManager | None = None,
        validator_manager: IValidatorManager | None = None,
        remediator_manager: IRemediatorManager | None = None,
        protocol_adapter_manager: IProtocolAdapterManager | None = None,
        hook_manager: IHookManager | None = None,
    ) -> TBuilder:
        """Inject component managers for config-driven resolution.

        Managers are only used when the corresponding component is not explicitly provided
        via builder methods (precedence rule).
        """
        if tool_manager is not None:
            self._tool_manager = tool_manager
        if model_adapter_manager is not None:
            self._model_adapter_manager = model_adapter_manager
        if planner_manager is not None:
            self._planner_manager = planner_manager
        if validator_manager is not None:
            self._validator_manager = validator_manager
        if remediator_manager is not None:
            self._remediator_manager = remediator_manager
        if protocol_adapter_manager is not None:
            self._protocol_adapter_manager = protocol_adapter_manager
        if hook_manager is not None:
            self._hook_manager = hook_manager
        return self

    def with_model(self: TBuilder, model: IModelAdapter) -> TBuilder:
        self._model = model
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

    def _refresh_tool_provider_sync(self, provider: GatewayToolProvider) -> None:
        """Synchronously refresh tool capabilities on a provider."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(provider.refresh())
            return
        raise RuntimeError(
            "Builder cannot refresh tool capabilities while an event loop is running. "
            "Build the agent before entering the async runtime or supply a custom tool provider."
        )

    def _ensure_tool_gateway(self, tools: list[ITool]) -> IToolGateway | None:
        """Return a ToolGateway if tool wiring requires one."""
        if self._tool_gateway is not None:
            return self._tool_gateway
        if tools:
            return DefaultToolGateway()
        return None

    def _wire_native_tools(self, gateway: IToolGateway, tools: list[ITool]) -> None:
        """Register tools into the tool gateway."""
        if not tools:
            return
        provider = NativeToolProvider(tools=tools, context_factory=self._run_context_factory)
        gateway.register_provider(provider)

    def _ensure_tool_provider(self, gateway: IToolGateway | None) -> IToolProvider | None:
        """Return a tool provider for Context.listing_tools()."""
        if self._tool_provider is not None:
            return self._tool_provider
        if gateway is None:
            return None
        provider = GatewayToolProvider(gateway)
        self._refresh_tool_provider_sync(provider)
        return provider

    def _resolved_model(self) -> IModelAdapter:
        if self._model is not None:
            return self._model

        manager = self._model_adapter_manager
        if manager is None:
            raise ValueError("Builder requires a model adapter (explicit or manager-resolved)")

        candidate = manager.load_model_adapter(config=self._manager_config())
        if candidate is None:
            raise ValueError("Model adapter manager did not return an IModelAdapter")
        return candidate

    def _resolved_tools(self) -> list[ITool]:
        explicit = list(self._tools)

        manager = self._tool_manager
        if manager is None:
            return explicit

        discovered = manager.load_tools(config=self._manager_config())
        manager_tools = [
            tool for tool in discovered if self._config is None or self._config.is_component_enabled(tool)
        ]
        return [*explicit, *manager_tools]


class SimpleChatAgentBuilder(_BaseAgentBuilder):
    """Builder for SimpleChatAgent."""

    def build(self) -> SimpleChatAgent:
        model = self._resolved_model()

        tools = self._resolved_tools()
        tool_gateway = self._ensure_tool_gateway(tools)
        if tool_gateway is not None:
            self._wire_native_tools(tool_gateway, tools)

        tool_provider = self._ensure_tool_provider(tool_gateway)

        if self._context is None:
            return SimpleChatAgent(
                name=self._name,
                model=model,
                short_term_memory=self._short_term_memory,
                long_term_memory=self._long_term_memory,
                knowledge=self._knowledge,
                tools=tool_provider,
                budget=self._budget,
            )

        self._apply_context_overrides(self._context)
        if tool_provider is not None:
            setattr(self._context, "_tool_provider", tool_provider)

        return SimpleChatAgent(
            name=self._name,
            model=model,
            context=self._context,
        )


class FiveLayerAgentBuilder(_BaseAgentBuilder):
    """Builder for FiveLayerAgent (five-layer orchestration)."""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self._planner: IPlanner | None = None
        self._validators: list[IValidator] = []
        self._remediator: IRemediator | None = None

        self._event_log: IEventLog | None = None
        self._execution_control: IExecutionControl | None = None
        self._hooks: list[IHook] = []

    def with_planner(self, planner: IPlanner) -> "FiveLayerAgentBuilder":
        self._planner = planner
        return self

    def add_validators(self, *validators: IValidator) -> "FiveLayerAgentBuilder":
        self._validators.extend(validators)
        return self

    def with_remediator(self, remediator: IRemediator) -> "FiveLayerAgentBuilder":
        self._remediator = remediator
        return self

    def with_event_log(self, event_log: IEventLog) -> "FiveLayerAgentBuilder":
        self._event_log = event_log
        return self

    def with_execution_control(self, execution_control: IExecutionControl) -> "FiveLayerAgentBuilder":
        self._execution_control = execution_control
        return self

    def add_hooks(self, *hooks: IHook) -> "FiveLayerAgentBuilder":
        self._hooks.extend(hooks)
        return self

    def build(self) -> FiveLayerAgent:
        model = self._resolved_model()

        tools = self._resolved_tools()
        tool_gateway = self._ensure_tool_gateway(tools)
        if tool_gateway is not None:
            self._wire_native_tools(tool_gateway, tools)
        tool_provider = self._ensure_tool_provider(tool_gateway)

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
            return FiveLayerAgent(
                name=self._name,
                model=model,
                short_term_memory=self._short_term_memory,
                long_term_memory=self._long_term_memory,
                tools=tool_provider,
                tool_gateway=tool_gateway,
                execution_control=self._execution_control,
                planner=planner,
                validator=validator,
                remediator=remediator,
                event_log=self._event_log,
                hooks=hooks,
                budget=self._budget,
            )

        self._apply_context_overrides(self._context)
        if tool_provider is not None:
            setattr(self._context, "_tool_provider", tool_provider)

        return FiveLayerAgent(
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
        )


class Builder:
    """Facade for selecting which builder variant to use."""

    @staticmethod
    def simple_chat_agent_builder(name: str) -> SimpleChatAgentBuilder:
        return SimpleChatAgentBuilder(name)

    @staticmethod
    def five_layer_agent_builder(name: str) -> FiveLayerAgentBuilder:
        return FiveLayerAgentBuilder(name)


__all__ = ["Builder", "FiveLayerAgentBuilder", "SimpleChatAgentBuilder"]
