"""Minimal AgentBuilder implementation."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable

from dare_framework.agent import SimpleChatAgent
from dare_framework.context import Context, Budget
from dare_framework.knowledge import IKnowledge
from dare_framework.memory import ILongTermMemory, IShortTermMemory
from dare_framework.model.interfaces import IModelAdapter
from dare_framework.tool._internal.gateway.default_tool_gateway import DefaultToolGateway
from dare_framework.tool._internal.providers.gateway_tool_provider import GatewayToolProvider
from dare_framework.tool._internal.providers.native_tool_provider import NativeToolProvider
from dare_framework.tool.interfaces import ITool, IToolProvider, RunContext
from dare_framework.tool.kernel import IToolGateway


class AgentBuilder:
    """Compose a minimal SimpleChatAgent with tools and context wiring."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._model: IModelAdapter | None = None
        self._context: Context | None = None
        self._budget: Budget | None = None
        self._short_term_memory: IShortTermMemory | None = None
        self._long_term_memory: ILongTermMemory | None = None
        self._knowledge: IKnowledge | None = None
        self._tools: list[ITool] = []
        self._tool_gateway: IToolGateway | None = None
        self._tool_provider: IToolProvider | None = None

    def with_model(self, model: IModelAdapter) -> "AgentBuilder":
        """Set the model adapter used by the agent."""
        self._model = model
        return self

    def with_context(self, context: Context) -> "AgentBuilder":
        """Provide a pre-built context instance."""
        self._context = context
        return self

    def with_budget(self, budget: Budget) -> "AgentBuilder":
        """Override the budget used by the context."""
        self._budget = budget
        return self

    def with_short_term_memory(self, memory: IShortTermMemory) -> "AgentBuilder":
        """Inject a short-term memory implementation."""
        self._short_term_memory = memory
        return self

    def with_long_term_memory(self, memory: ILongTermMemory) -> "AgentBuilder":
        """Inject a long-term memory implementation."""
        self._long_term_memory = memory
        return self

    def with_knowledge(self, knowledge: IKnowledge) -> "AgentBuilder":
        """Inject a knowledge retrieval implementation."""
        self._knowledge = knowledge
        return self

    def with_tools(self, *tools: ITool) -> "AgentBuilder":
        """Register local tools to expose through the tool gateway."""
        self._tools.extend(tools)
        return self

    def with_tool_gateway(self, gateway: IToolGateway) -> "AgentBuilder":
        """Provide a custom tool gateway implementation."""
        self._tool_gateway = gateway
        return self

    def with_tool_provider(self, provider: IToolProvider) -> "AgentBuilder":
        """Provide a custom tool provider for context assembly."""
        self._tool_provider = provider
        return self

    def build(self) -> SimpleChatAgent:
        """Build and return a SimpleChatAgent with configured wiring."""
        if self._model is None:
            raise ValueError("AgentBuilder requires a model adapter")

        tool_gateway = self._tool_gateway
        if tool_gateway is None and self._tools:
            tool_gateway = DefaultToolGateway()

        if self._tools and tool_gateway is not None:
            provider = NativeToolProvider(
                tools=list(self._tools),
                context_factory=self._default_run_context,
            )
            tool_gateway.register_provider(provider)

        tool_provider = self._tool_provider
        if tool_provider is None and tool_gateway is not None:
            if self._tools or self._tool_gateway is not None:
                tool_provider = GatewayToolProvider(tool_gateway)
                self._refresh_tool_provider_sync(tool_provider)

        if self._context is None:
            return SimpleChatAgent(
                name=self._name,
                model=self._model,
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
            model=self._model,
            context=self._context,
        )

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
            "AgentBuilder.build() cannot refresh tool capabilities while an event loop is running. "
            "Build the agent before entering the async runtime or supply a custom tool provider."
        )


__all__ = ["AgentBuilder"]
