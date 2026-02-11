"""Default context implementation (context-centric)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from dare_framework.config.types import Config
from dare_framework.tool.kernel import IToolGateway
from dare_framework.tool.types import CapabilityDescriptor

if TYPE_CHECKING:
    from dare_framework.model.types import Prompt
    from dare_framework.skill.types import Skill

from dare_framework.context.kernel import IContext, IRetrievalContext, IAssembleContext
from dare_framework.context.types import AssembledContext, Budget, Message


# ============================================================
# Implementation
# ============================================================

class Context(IContext):
    """Context implementation.

    Messages are NOT stored as a field, but assembled on-demand via assemble().
    """

    def __init__(
            self,
            id: str | None = None,
            budget: Budget | None = None,
            *,
            config: Config,
            short_term_memory: IRetrievalContext | None = None,
            long_term_memory: IRetrievalContext | None = None,
            knowledge: IRetrievalContext | None = None,
            tool_gateway: IToolGateway | None = None,
            sys_prompt: Prompt | None = None,
            skill: Skill | None = None,
            assemble_context: IAssembleContext | None = None,
    ) -> None:
        if config is None:
            raise ValueError("Context requires a non-null Config")
        self._id = id or str(uuid.uuid4())
        self._budget = budget or Budget()
        self._config = config
        self._short_term_memory = short_term_memory
        self._long_term_memory = long_term_memory
        self._knowledge = knowledge
        self._tool_gateway = tool_gateway
        self._sys_prompt = sys_prompt

        # Current skill (one at a time; injected at assemble time)
        self._sys_skill = skill

        self._assemble_context = assemble_context or DefaultAssembledContext()

        # Initialize default short-term memory if not provided
        if self._short_term_memory is None:
            from dare_framework.memory.in_memory_stm import InMemorySTM
            self._short_term_memory = InMemorySTM()

    @property
    def id(self) -> str:
        return self._id

    @property
    def budget(self) -> Budget:
        return self._budget

    @property
    def short_term_memory(self) -> IRetrievalContext:
        return self._short_term_memory

    @property
    def long_term_memory(self) -> IRetrievalContext | None:
        return self._long_term_memory

    @property
    def knowledge(self) -> IRetrievalContext | None:
        return self._knowledge

    @property
    def config(self) -> Config:
        return self._config

    @property
    def tool_gateway(self) -> IToolGateway | None:
        return self._tool_gateway

    @property
    def sys_prompt(self) -> Prompt | None:
        return self._sys_prompt

    @property
    def sys_skill(self) -> Skill | None:
        return self._sys_skill

    # ========== Short-term Memory Methods ==========

    def stm_add(self, message: Message) -> None:
        """Add a message to short-term memory."""
        self._short_term_memory.add(message)  # type: ignore

    def stm_get(self) -> list[Message]:
        """Get all messages from short-term memory."""
        return self._short_term_memory.get()

    def stm_clear(self) -> list[Message]:
        """Clear short-term memory, returns empty list."""
        self._short_term_memory.clear()  # type: ignore
        return []

    # ========== Budget Methods ==========

    def budget_use(self, resource: str, amount: float) -> None:
        """Record resource consumption."""
        if resource == "tokens":
            self._budget.used_tokens += amount
        elif resource == "cost":
            self._budget.used_cost += amount
        elif resource == "time_seconds":
            self._budget.used_time_seconds += amount
        elif resource == "tool_calls":
            self._budget.used_tool_calls += int(amount)

    def budget_check(self) -> None:
        """Check if any budget limit is exceeded."""
        b = self._budget
        if b.max_tokens is not None and b.used_tokens > b.max_tokens:
            raise RuntimeError(
                f"Token budget exceeded: {b.used_tokens}/{b.max_tokens}"
            )
        if b.max_cost is not None and b.used_cost > b.max_cost:
            raise RuntimeError(
                f"Cost budget exceeded: {b.used_cost}/{b.max_cost}"
            )
        if b.max_tool_calls is not None and b.used_tool_calls > b.max_tool_calls:
            raise RuntimeError(
                f"Tool call budget exceeded: {b.used_tool_calls}/{b.max_tool_calls}"
            )
        if b.max_time_seconds is not None and b.used_time_seconds > b.max_time_seconds:
            raise RuntimeError(
                f"Time budget exceeded: {b.used_time_seconds}/{b.max_time_seconds}"
            )

    def budget_remaining(self, resource: str) -> float:
        """Get remaining budget for a resource."""
        b = self._budget
        if resource == "tokens":
            return (b.max_tokens - b.used_tokens) if b.max_tokens else float("inf")
        elif resource == "cost":
            return (b.max_cost - b.used_cost) if b.max_cost else float("inf")
        elif resource == "tool_calls":
            return (b.max_tool_calls - b.used_tool_calls) if b.max_tool_calls else float("inf")
        elif resource == "time_seconds":
            return (b.max_time_seconds - b.used_time_seconds) if b.max_time_seconds else float("inf")
        return float("inf")

    # ========== Tool Methods ==========

    def set_tool_gateway(self, tool_gateway: IToolGateway | None) -> None:
        self._tool_gateway = tool_gateway

    def list_tools(self) -> list[CapabilityDescriptor]:
        """Get tool list from a ToolManager or provider."""
        if self._tool_gateway is not None:
            return self._tool_gateway.list_capabilities()
        return []

    # ========== Assembly Methods (Core) ==========

    def assemble(self) -> AssembledContext:
        return self._assemble_context.assemble(self)

    def compress(self, **options: Any) -> None:
        """Compress context to fit within budget."""
        if self._short_term_memory is not None:
            self._short_term_memory.compress(**options)


class DefaultAssembledContext(IAssembleContext):

    def assemble(self, context: IContext) -> AssembledContext:
        messages = context.stm_get()
        tools = context.list_tools()
        sys_prompt = context.sys_prompt
        if context.sys_skill is not None and sys_prompt is not None:
            from dare_framework.skill._internal.prompt_enricher import enrich_prompt_with_skill

            sys_prompt = enrich_prompt_with_skill(sys_prompt, context.sys_skill)
        return AssembledContext(
            messages=messages,
            sys_prompt=sys_prompt,
            tools=tools,
            metadata={
                "context_id": context.id,
            },
        )


__all__ = [
    "Message",
    "Budget",
    "AssembledContext",
    "IRetrievalContext",
    "IContext",
    "Context",
]
