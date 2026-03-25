"""Default context implementation (context-centric)."""

from __future__ import annotations

import math
import uuid
from typing import TYPE_CHECKING, Any

from dare_framework.config.types import Config
from dare_framework.tool.kernel import IToolGateway
from dare_framework.tool.types import CapabilityDescriptor

if TYPE_CHECKING:
    from dare_framework.compression.moving_compression import MovingCompressor
    from dare_framework.guidance.guidance_queue import GuidanceQueue
    from dare_framework.model.types import Prompt
    from dare_framework.skill.types import Skill

from dare_framework.context.kernel import IContext, IRetrievalContext, IAssembleContext
from dare_framework.context.types import AssembledContext, Budget, Message, MessageKind, MessageRole


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
            context_window_tokens: int | None = None,
            moving_compressor: MovingCompressor | None = None,
            guidance_queue: GuidanceQueue | None = None,
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
        # 单次请求上下文窗口大小（用于压缩）；None 表示由调用方或压缩器自行决定。
        self._context_window_tokens: int | None = (
            int(context_window_tokens) if context_window_tokens and context_window_tokens > 0 else None
        )

        # Current skill (one at a time; injected at assemble time)
        self._sys_skill = skill

        self._assemble_context = assemble_context or DefaultAssembledContext()

        # 可选：移动窗口压缩器，通过 moving_compressor.prune(self) 使用
        self._moving_compressor = moving_compressor

        # 可选：用户引导队列，在 assemble() 时自动排空注入到 STM
        self._guidance_queue: GuidanceQueue | None = guidance_queue

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

    def set_skill(self, skill: Skill | None) -> None:
        """Mount or replace current skill at runtime. None clears."""
        self._sys_skill = skill

    @property
    def context_window_tokens(self) -> int | None:
        """LLM 单次请求上下文窗口大小（用于压缩），单位 token。"""
        return self._context_window_tokens

    @property
    def moving_compressor(self) -> MovingCompressor | None:
        """可选挂载的移动窗口压缩器；未挂载时为 None。"""
        return self._moving_compressor

    def set_moving_compressor(self, compressor: MovingCompressor | None) -> None:
        """挂载或卸载移动窗口压缩器。"""
        self._moving_compressor = compressor

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

    def _drain_guidance(self) -> None:
        """Drain pending guidance items into STM.

        Called before compression and assembly so that guidance messages
        participate in token-budget pruning and appear in the assembled
        context exactly once.
        """
        if self._guidance_queue is None:
            return
        items = self._guidance_queue.drain_all_sync()
        for item in items:
            self.stm_add(Message(
                role=MessageRole.USER,
                kind=MessageKind.CHAT,
                text=item.content,
                metadata={"guidance_id": item.id, "source": "user_guidance"},
            ))

    def assemble(self) -> AssembledContext:
        self._drain_guidance()
        return self._assemble_context.assemble(self)

    async def compress(self, **options: Any) -> None:
        """压缩 STM：仅委托 moving_compressor.prune；无 compressor 时无操作。"""
        if self._moving_compressor is None:
            return
        # 只把与 token 预算相关的参数传给压缩器；摘要 prompt 与语言策略由压缩器内部自行决定。
        prune_opts: dict[str, Any] = {}
        if "max_context_tokens" in options:
            prune_opts["max_context_tokens"] = options["max_context_tokens"]
        elif self._context_window_tokens is not None and self._context_window_tokens > 0:
            prune_opts["max_context_tokens"] = self._context_window_tokens
        await self._moving_compressor.prune(self, **prune_opts)

    async def assemble_for_model(self, **options: Any) -> AssembledContext:
        """供模型调用的装配入口：先排空引导队列，再压缩，最后装配。

        Guidance is drained **before** compression so that guidance messages
        participate in token-budget pruning and do not silently push the
        final prompt over the configured context window.
        """
        self._drain_guidance()
        await self.compress(**options)
        return self.assemble()


class DefaultAssembledContext(IAssembleContext):
    """Default context assembly strategy.
    """

    def assemble(self, context: IContext) -> AssembledContext:
        messages = context.stm_get()
        tools = context.list_tools()
        sys_prompt = context.sys_prompt
        if context.sys_skill is not None and sys_prompt is not None:
            from dare_framework.skill._internal.prompt_enricher import enrich_prompt_with_skill

            sys_prompt = enrich_prompt_with_skill(sys_prompt, context.sys_skill)

        return AssembledContext(
            messages=list(messages),
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
