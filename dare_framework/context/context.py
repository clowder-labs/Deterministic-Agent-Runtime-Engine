"""Default context implementation (context-centric)."""

from __future__ import annotations

import math
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
        from dare_framework.compression.core import compress_context

        # Preserve backend STM semantics (for example SmartSTM mark-based retention)
        # before applying advanced compression strategies.
        compress_impl = getattr(self._short_term_memory, "compress", None)
        has_advanced_options = any(
            key in options
            for key in ("target_tokens", "tool_pair_safe", "strategy", "phase")
        )
        raw_max_messages = options.get("max_messages")
        max_messages = (
            raw_max_messages
            if isinstance(raw_max_messages, int) and raw_max_messages >= 0
            else None
        )
        if callable(compress_impl):
            if not has_advanced_options:
                compress_impl(max_messages=max_messages)
                return
            if max_messages is not None:
                compress_impl(max_messages=max_messages)

        compress_context(self, **options)


class DefaultAssembledContext(IAssembleContext):
    """Default context assembly strategy.

    Baseline behavior:
    - Use STM as primary conversation state.
    - Optionally fuse LTM/Knowledge retrieval messages.
    - Degrade retrieval under low remaining token budget.
    """

    _DEFAULT_TOP_K = 3
    _DEFAULT_RESERVE_TOKENS = 256
    _DEFAULT_SOURCE_RATIO = 0.5

    def _safe_int(self, value: Any, default: int, *, minimum: int | None = None) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError, OverflowError):
            parsed = default
        if minimum is not None:
            parsed = max(minimum, parsed)
        return parsed

    def _safe_ratio(self, value: Any) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError, OverflowError):
            return self._DEFAULT_SOURCE_RATIO
        if not math.isfinite(parsed) or parsed < 0:
            return self._DEFAULT_SOURCE_RATIO
        return parsed

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimate using character count heuristic."""
        total = 0
        for message in messages:
            # Roughly 4 chars/token + small per-message overhead.
            content_tokens = max(1, len((message.content or "").strip()) // 4)
            total += content_tokens + 8
        return total

    def _take_with_budget(self, messages: list[Message], budget_tokens: float) -> list[Message]:
        if budget_tokens == float("inf"):
            return list(messages)
        if budget_tokens <= 0:
            return []

        kept: list[Message] = []
        used = 0
        for message in messages:
            message_tokens = self._estimate_tokens([message])
            if used + message_tokens > budget_tokens:
                # Skip oversized candidates so smaller later hits can still fit.
                continue
            kept.append(message)
            used += message_tokens
        return kept

    def _derive_query(self, messages: list[Message]) -> str:
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message.content.strip()
        for message in reversed(messages):
            if message.content.strip():
                return message.content.strip()
        return ""

    def _load_source_options(self, config_map: dict[str, Any]) -> tuple[int, float]:
        top_k = self._safe_int(
            config_map.get("assemble_top_k"),
            self._DEFAULT_TOP_K,
            minimum=0,
        )
        ratio = self._safe_ratio(config_map.get("assemble_ratio", self._DEFAULT_SOURCE_RATIO))
        return top_k, ratio

    def _set_degrade(
        self,
        retrieval_metadata: dict[str, Any],
        *,
        reason: str,
    ) -> None:
        retrieval_metadata["degraded"] = True
        retrieval_metadata["degrade_reason"] = reason

    def assemble(self, context: IContext) -> AssembledContext:
        messages = context.stm_get()
        tools = context.list_tools()
        sys_prompt = context.sys_prompt
        if context.sys_skill is not None and sys_prompt is not None:
            from dare_framework.skill._internal.prompt_enricher import enrich_prompt_with_skill

            sys_prompt = enrich_prompt_with_skill(sys_prompt, context.sys_skill)

        query = self._derive_query(messages)
        ltm_config = context.config.long_term_memory if isinstance(context.config.long_term_memory, dict) else {}
        knowledge_config = context.config.knowledge if isinstance(context.config.knowledge, dict) else {}
        ltm_top_k, ltm_ratio = self._load_source_options(ltm_config)
        knowledge_top_k, knowledge_ratio = self._load_source_options(knowledge_config)
        ltm_active = context.long_term_memory is not None and ltm_top_k > 0
        knowledge_active = context.knowledge is not None and knowledge_top_k > 0

        if ltm_active and not knowledge_active:
            reserve_tokens_raw = ltm_config.get("assemble_reserve_tokens")
        elif knowledge_active and not ltm_active:
            reserve_tokens_raw = knowledge_config.get("assemble_reserve_tokens")
        else:
            reserve_tokens_raw = ltm_config.get("assemble_reserve_tokens")
            if reserve_tokens_raw is None:
                reserve_tokens_raw = knowledge_config.get("assemble_reserve_tokens")
        reserve_tokens = self._safe_int(
            reserve_tokens_raw,
            self._DEFAULT_RESERVE_TOKENS,
            minimum=0,
        )

        retrieval_metadata: dict[str, Any] = {
            "query": query,
            "stm_count": len(messages),
            "ltm_requested": ltm_top_k,
            "knowledge_requested": knowledge_top_k,
            "ltm_count": 0,
            "knowledge_count": 0,
            "degraded": False,
            "degrade_reason": None,
        }

        remaining_tokens = context.budget_remaining("tokens")
        stm_token_estimate = self._estimate_tokens(messages)
        retrieval_budget: float = float("inf")
        if remaining_tokens != float("inf"):
            retrieval_budget = max(0.0, float(remaining_tokens) - float(stm_token_estimate) - float(reserve_tokens))

        ltm_messages: list[Message] = []
        knowledge_messages: list[Message] = []

        if retrieval_budget <= 0 and (ltm_active or knowledge_active):
            self._set_degrade(retrieval_metadata, reason="token_budget_low")
        else:
            ratio_total = 0.0
            if ltm_active:
                ratio_total += ltm_ratio
            if knowledge_active:
                ratio_total += knowledge_ratio
            if ratio_total <= 0:
                # Fallback only across active retrieval sources.
                ratio_total = 0.0
                if ltm_active:
                    ltm_ratio = self._DEFAULT_SOURCE_RATIO
                    ratio_total += ltm_ratio
                if knowledge_active:
                    knowledge_ratio = self._DEFAULT_SOURCE_RATIO
                    ratio_total += knowledge_ratio

            normalized_ltm_ratio = (ltm_ratio / ratio_total) if ltm_active and ratio_total > 0 else 0.0
            normalized_knowledge_ratio = (
                (knowledge_ratio / ratio_total) if knowledge_active and ratio_total > 0 else 0.0
            )

            ltm_budget = float("inf")
            knowledge_budget = float("inf")
            if retrieval_budget != float("inf"):
                ltm_budget = retrieval_budget * normalized_ltm_ratio
                knowledge_budget = retrieval_budget * normalized_knowledge_ratio

            ltm_retrieval_failed = False
            if ltm_active:
                if ltm_budget <= 0:
                    ltm_messages = []
                else:
                    try:
                        ltm_candidates = context.long_term_memory.get(query=query, top_k=ltm_top_k)
                        ltm_messages = self._take_with_budget(ltm_candidates, ltm_budget)
                        if len(ltm_messages) < len(ltm_candidates):
                            self._set_degrade(retrieval_metadata, reason="token_budget_low")
                    except Exception:
                        ltm_retrieval_failed = True
                        self._set_degrade(retrieval_metadata, reason="ltm_retrieval_failed")
                        ltm_messages = []

            if knowledge_active:
                try:
                    effective_knowledge_budget = knowledge_budget
                    if (
                        retrieval_budget != float("inf")
                        and ltm_active
                        and ltm_retrieval_failed
                    ):
                        effective_knowledge_budget = retrieval_budget
                    if effective_knowledge_budget <= 0:
                        knowledge_messages = []
                    else:
                        knowledge_candidates = context.knowledge.get(query=query, top_k=knowledge_top_k)
                        knowledge_messages = self._take_with_budget(knowledge_candidates, effective_knowledge_budget)
                        if len(knowledge_messages) < len(knowledge_candidates):
                            self._set_degrade(retrieval_metadata, reason="token_budget_low")
                except Exception:
                    if not retrieval_metadata["degraded"]:
                        self._set_degrade(retrieval_metadata, reason="knowledge_retrieval_failed")
                    knowledge_messages = []

        merged_messages = [*messages, *ltm_messages, *knowledge_messages]
        retrieval_metadata["ltm_count"] = len(ltm_messages)
        retrieval_metadata["knowledge_count"] = len(knowledge_messages)

        return AssembledContext(
            messages=merged_messages,
            sys_prompt=sys_prompt,
            tools=tools,
            metadata={
                "context_id": context.id,
                "retrieval": retrieval_metadata,
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
