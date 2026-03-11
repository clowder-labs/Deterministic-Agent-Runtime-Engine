"""Smart context - extends Context with additional capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework.context.context import Context
from dare_framework.context.types import Message, MessageMark
from dare_framework.memory.in_memory_smart_stm import InMemorySmartSTM

if TYPE_CHECKING:
    from dare_framework.config.types import Config
    from dare_framework.guidance.guidance_queue import GuidanceQueue
    from dare_framework.model.types import Prompt
    from dare_framework.skill.types import Skill
    from dare_framework.tool.kernel import IToolGateway
    from dare_framework.context.kernel import IRetrievalContext, IAssembleContext
    from dare_framework.context.types import Budget


class SmartContext(Context):
    """Extended context implementation.

    Inherits all Context behavior. Add new capabilities here without
    modifying the base Context.
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
        guidance_queue: GuidanceQueue | None = None,
    ) -> None:
        # SmartContext 默认使用带 id/mark 能力的 InMemorySmartSTM，
        # 仅当外部显式传入 short_term_memory 时才使用外部实现。
        if short_term_memory is None:
            short_term_memory = InMemorySmartSTM()

        super().__init__(
            id=id,
            budget=budget,
            config=config,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            knowledge=knowledge,
            tool_gateway=tool_gateway,
            sys_prompt=sys_prompt,
            skill=skill,
            assemble_context=assemble_context,
            context_window_tokens=context_window_tokens,
            guidance_queue=guidance_queue,
        )

    # ========== Smart Extensions: Core / TaskComplete / STM Remove ==========

    def stm_remove_by_ids(self, ids: list[str]) -> int:
        """Remove TEMPORARY messages with id in ids. Returns count removed."""
        stm = self._short_term_memory
        if hasattr(stm, "remove_by_ids"):
            return stm.remove_by_ids(ids)
        return 0

    def update_core(self, content: str) -> None:
        """Update or create the single CORE message. CORE holds persistent task summary."""
        messages = self._short_term_memory.get()
        for m in messages:
            mid = getattr(m, "id", None)
            if mid == "core" or (getattr(m, "mark", None) == MessageMark.PERSISTENT and mid != "task_complete"):
                object.__setattr__(m, "text", content)
                if mid != "core":
                    object.__setattr__(m, "id", "core")
                return
        core_msg = Message(role="system", text=content, mark=MessageMark.PERSISTENT, id="core")
        self.stm_add(core_msg)

    def update_task_complete(self, value: bool) -> None:
        """Update or create the task_complete message. Separate from core; agent can read task completion status."""
        messages = self._short_term_memory.get()
        content = "true" if value else "false"
        for m in messages:
            if getattr(m, "id", None) == "task_complete":
                object.__setattr__(m, "text", content)
                return
        task_complete_msg = Message(
            role="system",
            text=content,
            mark=MessageMark.PERSISTENT,
            id="task_complete",
        )
        self.stm_add(task_complete_msg)

    def get_task_complete(self) -> bool:
        """Read task_complete from the dedicated message. Returns False if not found."""
        messages = self._short_term_memory.get()
        for m in messages:
            if getattr(m, "id", None) == "task_complete":
                return (getattr(m, "text", "") or "").strip().lower() in ("true", "1", "yes")
        return False

    def order_messages_for_llm(
        self,
        messages: list[Message],
        sys_prompt_message: Message | None = None,
        *,
        add_id_mark_prefix: bool = True,
    ) -> list[Message]:
        """Order messages for LLM input: core → task_complete → user_task → sys_prompt → rest.

        user_task before sys_prompt to prioritize user/upper task requirements.
        rest messages are sorted by mark: IMMUTABLE → PERSISTENT → TEMPORARY.
        When add_id_mark_prefix=True, prepends [id=xxx, mark=yyy] for model visibility.
        """
        front_ids = {"core", "task_complete", "user_task"}
        core_msgs = [m for m in messages if getattr(m, "id", None) == "core"]
        task_complete_msgs = [m for m in messages if getattr(m, "id", None) == "task_complete"]
        user_task_msgs = [m for m in messages if getattr(m, "id", None) == "user_task"]
        rest_msgs = [m for m in messages if getattr(m, "id", None) not in front_ids]
        ordered: list[Message] = []
        ordered.extend(core_msgs)
        ordered.extend(task_complete_msgs)
        ordered.extend(user_task_msgs)
        if sys_prompt_message is not None:
            ordered.append(sys_prompt_message)
        ordered.extend(_sort_messages_by_mark(rest_msgs))
        if add_id_mark_prefix:
            ordered = _add_id_mark_prefix(ordered)
        return ordered


def _add_id_mark_prefix(msgs: list[Message]) -> list[Message]:
    """Prepend [id=xxx, mark=yyy] to each message content for model visibility."""
    result = []
    for m in msgs:
        mid = getattr(m, "id", None) or "-"
        mmark = getattr(m, "mark", MessageMark.TEMPORARY)
        mval = mmark.value if hasattr(mmark, "value") else str(mmark)
        if mid == "core":
            prefix = "[CORE - 地位核心，跨轮保留；进度/结论须写入此处否则会丢失]\n"
        elif mid == "task_complete":
            prefix = "[TASK_COMPLETE - 决定 agent 能否结束，true 才能结束]\n"
        elif mid == "user_task":
            prefix = "[USER_TASK - 用户/上层任务需求；判断 task_complete 时必须对照此需求是否已全部满足]\n"
        else:
            prefix = f"[id={mid}, mark={mval}]\n"
        result.append(Message(
            role=m.role,
            kind=m.kind,
            text=prefix + (m.text or ""),
            attachments=list(m.attachments),
            data=dict(m.data) if m.data is not None else None,
            name=m.name,
            metadata=dict(m.metadata),
            mark=m.mark,
            id=m.id,
        ))
    return result


def _sort_messages_by_mark(msgs: list[Message]) -> list[Message]:
    """Order: IMMUTABLE -> PERSISTENT -> TEMPORARY, preserve order within each group."""
    imm, persistent, tmp = [], [], []
    for m in msgs:
        mark = getattr(m, "mark", MessageMark.TEMPORARY)
        if mark == MessageMark.IMMUTABLE:
            imm.append(m)
        elif mark == MessageMark.PERSISTENT:
            persistent.append(m)
        else:
            tmp.append(m)
    return imm + persistent + tmp


__all__ = ["SmartContext"]
