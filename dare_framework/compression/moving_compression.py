"""Token-aware, moving-window STM compression (OpenClaw-style).

本模块提供一套“滑动窗口式”的上下文压缩算法，思路参考
`openclaw/openclaw/src/agents/compaction.ts` 的 `pruneHistoryForContextShare`：

- 针对当前 STM（短期记忆）中的消息，按 **token 预算** 决定能保留多少历史；
- 通过按 token 均匀分块，反复丢弃“最老的一块”，直到剩余消息的 token 总数
  落在预算之内；
- 丢弃块后，对保留的消息执行工具调用对偶修复，避免出现孤立的 tool/tool_result。
- 必须挂载 model；压缩时对丢弃的消息调用 LLM 做摘要，再将「一条摘要 + 保留消息」写回 STM。

本实现自包含，不依赖 compression.core。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from dare_framework.context.types import Message, MessageMark

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.model.kernel import IModelAdapter


# ---------------------------------------------------------------------------
# Token 估算（字符启发式，与 core 语义一致，本模块内自实现）
# ---------------------------------------------------------------------------


def _estimate_tokens(messages: List[Message]) -> int:
    """Rough token estimate: ~4 chars/token + 8 per message overhead."""
    total = 0
    for msg in messages:
        content = (msg.text or "").strip()
        attachment_tokens = len(msg.attachments) * 32
        total += max(1, len(content) // 4) + attachment_tokens + 8
    return total


# ---------------------------------------------------------------------------
# 工具调用对偶修复（保证 tool_call 与 tool result 成对，无孤立项）
# ---------------------------------------------------------------------------


def _extract_tool_call_ids(message: Message) -> List[str]:
    """Collect tool call ids from an assistant message's canonical data payload."""
    if message.role != "assistant":
        return []
    tool_calls = message.data.get("tool_calls", []) if isinstance(message.data, dict) else []
    if not isinstance(tool_calls, list):
        return []
    ids: List[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        tool_id = call.get("id")
        if isinstance(tool_id, str) and tool_id.strip():
            ids.append(tool_id.strip())
    return ids


def _enforce_tool_pair_safety(messages: List[Message]) -> Tuple[List[Message], int]:
    """Keep tool_call/tool_result in sync: drop orphan calls or results."""
    tool_result_ids = {
        message.name.strip()
        for message in messages
        if message.role == "tool"
        and isinstance(message.name, str)
        and message.name.strip()
    }

    updated_messages: List[Message] = []
    retained_call_ids: set[str] = set()
    retained_idless_tool_names: set[str] = set()
    changes = 0

    for message in messages:
        if message.role != "assistant":
            updated_messages.append(message)
            continue
        raw_calls = message.data.get("tool_calls", []) if isinstance(message.data, dict) else []
        if not isinstance(raw_calls, list):
            updated_messages.append(message)
            continue

        filtered_calls: List[dict] = []
        for call in raw_calls:
            if not isinstance(call, dict):
                continue
            tool_id = call.get("id")
            if (
                isinstance(tool_id, str)
                and tool_id.strip()
                and tool_id.strip() in tool_result_ids
            ):
                filtered_calls.append(call)
                retained_call_ids.add(tool_id.strip())
                continue
            if not isinstance(tool_id, str) or not tool_id.strip():
                filtered_calls.append(call)
                tool_name = call.get("name")
                if isinstance(tool_name, str) and tool_name.strip():
                    retained_idless_tool_names.add(tool_name.strip())

        if len(filtered_calls) != len(raw_calls):
            changes += len(raw_calls) - len(filtered_calls)
            data = dict(message.data) if isinstance(message.data, dict) else {}
            data["tool_calls"] = filtered_calls
            updated_messages.append(
                Message(
                    role=message.role,
                    kind=message.kind,
                    text=message.text,
                    attachments=list(message.attachments),
                    data=data,
                    name=message.name,
                    metadata=dict(message.metadata),
                    mark=getattr(message, "mark", MessageMark.TEMPORARY),
                    id=getattr(message, "id", None),
                )
            )
        else:
            retained_call_ids.update(_extract_tool_call_ids(message))
            updated_messages.append(message)

    final_messages: List[Message] = []
    for message in updated_messages:
        if message.role == "tool":
            tool_id = message.name.strip() if isinstance(message.name, str) else ""
            if tool_id in retained_call_ids or (
                tool_id and tool_id in retained_idless_tool_names
            ):
                final_messages.append(message)
                continue
            if tool_id:
                changes += 1
                continue
        final_messages.append(message)

    return final_messages, changes


def _move_tool_results_whose_calls_are_dropped(
    kept_messages: List[Message],
    dropped_messages: List[Message],
) -> Tuple[List[Message], List[Message], int]:
    """Move tool results into dropped when their calls live in dropped history.

    语义：
    - 若某条 tool result 的 name（通常是 tool_call id）在 dropped 段中的 assistant.tool_calls 里出现，
      说明对应的调用上下文已被视为「旧历史」；
    - 此时应将该 tool result 一并视为旧历史，移动到 dropped_messages 中，以便后续一起进入摘要，
      而不是在 kept 窗口里被视为“孤立结果”直接丢弃。
    """
    # 收集 dropped 段中的所有 tool_call id。
    dropped_call_ids: set[str] = set()
    for message in dropped_messages:
        if message.role != "assistant":
            continue
        for tool_id in _extract_tool_call_ids(message):
            if tool_id:
                dropped_call_ids.add(tool_id)

    if not dropped_call_ids or not kept_messages:
        return kept_messages, dropped_messages, 0

    new_kept: List[Message] = []
    moved = 0

    for message in kept_messages:
        if (
            message.role == "tool"
            and isinstance(message.name, str)
            and message.name.strip()
            and message.name.strip() in dropped_call_ids
        ):
            dropped_messages.append(message)
            moved += 1
        else:
            new_kept.append(message)

    return new_kept, dropped_messages, moved


# ---------------------------------------------------------------------------
# 按 token 均分块（OpenClaw splitMessagesByTokenShare 思路）
# ---------------------------------------------------------------------------


def _split_messages_by_token_share(
    messages: List[Message],
    parts: int,
) -> List[List[Message]]:
    """Split messages into `parts` chunks with roughly equal token mass."""
    if not messages:
        return []

    parts = max(1, int(parts))
    if parts == 1:
        return [messages]

    total_tokens = _estimate_tokens(messages)
    if total_tokens <= 0:
        return [messages]

    target_tokens = total_tokens / float(parts)
    chunks: List[List[Message]] = []
    current: List[Message] = []
    current_tokens = 0

    for msg in messages:
        msg_tokens = _estimate_tokens([msg])
        if (
            len(chunks) < parts - 1
            and current
            and current_tokens + msg_tokens > target_tokens
        ):
            chunks.append(current)
            current = []
            current_tokens = 0
        current.append(msg)
        current_tokens += msg_tokens

    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# 内部：只计算 kept/dropped，不写 STM（供 prune 与 prune_with_summary 复用）
# ---------------------------------------------------------------------------


def _compute_prune_result(
    messages: List[Message],
    budget_tokens: int,
    parts: int = 2,
    tool_pair_safe: bool = True,
) -> Tuple[List[Message], List[Message], Dict[str, Any]]:
    """按 token 预算计算应保留与丢弃的消息，不写 STM。返回 (kept, dropped, stats)。"""
    kept_messages: List[Message] = list(messages)
    dropped_messages: List[Message] = []
    dropped_chunks = 0
    dropped_tokens = 0
    parts = max(1, int(parts))

    while kept_messages and _estimate_tokens(kept_messages) > budget_tokens:
        chunks = _split_messages_by_token_share(kept_messages, parts=parts)
        if len(chunks) <= 1:
            break
        dropped = chunks[0]
        rest_flat: List[Message] = [m for chunk in chunks[1:] for m in chunk]
        dropped_chunks += 1
        dropped_messages.extend(dropped)
        dropped_tokens += _estimate_tokens(dropped)
        kept_messages = rest_flat

    if tool_pair_safe:
        # 只处理由「分块裁剪」直接引入的跨集合拆分：
        # - 若某个 tool result 的调用已被视为旧历史（在 dropped 中），
        #   则将该 tool result 一并并入 dropped，以便后续摘要。
        # 不再在此处对 kept 窗口内做第二次孤儿检测，避免把「历史上已经存在的结构问题」
        # 混入压缩职责；后续若需要全局清洗，可以在 Context 级别统一处理。
        kept_messages, dropped_messages, _ = _move_tool_results_whose_calls_are_dropped(
            kept_messages,
            dropped_messages,
        )

    stats: Dict[str, Any] = {
        "messages": kept_messages,
        "dropped_messages": dropped_messages,
        "dropped_chunks": dropped_chunks,
        "dropped_messages_count": len(dropped_messages),
        # 由于在对偶修复阶段可能出现跨集合移动，最终 token 统计需基于最新列表重新估算。
        "dropped_tokens": _estimate_tokens(dropped_messages),
        "kept_tokens": _estimate_tokens(kept_messages),
        "budget_tokens": budget_tokens,
    }
    return kept_messages, dropped_messages, stats


def _write_stm(context: IContext, messages: List[Message]) -> None:
    """将消息列表写回 context 的 STM。"""
    stm_clear = getattr(context, "stm_clear", None)
    stm_add = getattr(context, "stm_add", None)
    if not callable(stm_clear) or not callable(stm_add):
        return
    stm_clear()
    for msg in messages:
        if getattr(msg, "mark", None) is None:
            object.__setattr__(msg, "mark", MessageMark.TEMPORARY)
        stm_add(msg)


# ---------------------------------------------------------------------------
# LLM 摘要：对一段消息列表生成摘要文本（供 prune_with_summary 使用）
# ---------------------------------------------------------------------------

# 每条约 512 字符截断，与 core.compress_context_llm_summary 一致
_SUMMARY_SNIPPET_MAX = 512

_DEFAULT_SUMMARY_SYSTEM_ZH = (
    "你是一个对话摘要助手，请在不丢失关键信息的前提下，"
    "用简洁、结构化的方式总结下面的一段历史对话。"
    "可以合并重复信息，但不要编造不存在的内容。"
)
_DEFAULT_SUMMARY_SYSTEM_EN = (
    "You are a conversation summarization assistant. "
    "Produce a concise, structured summary of the following history, "
    "preserving key facts and decisions. Do not invent new information."
)
_USER_INTRO_ZH = (
    "下面是一段需要被压缩的历史对话，请输出一个摘要，用于后续继续对话使用。\n\n"
    "=== 历史开始 ===\n"
    "{conversation}\n"
    "=== 历史结束 ==="
)
_USER_INTRO_EN = (
    "Here is the conversation history that needs to be compressed. "
    "Please output a summary that can be used for continuing the dialogue.\n\n"
    "=== HISTORY START ===\n"
    "{conversation}\n"
    "=== HISTORY END ==="
)


async def _summarize_messages_to_text(
    messages: List[Message],
    model: IModelAdapter,
    *,
    system_prompt: str | None = None,
    language: str = "zh",
) -> str:
    """对 messages 调用 model 生成摘要文本。无 model 依赖时不调用。"""
    if not messages:
        return ""
    lines: List[str] = []
    for msg in messages:
        content = (msg.text or "").strip()
        if not content:
            continue
        snippet = content.replace("\n", " ")
        if len(snippet) > _SUMMARY_SNIPPET_MAX:
            snippet = snippet[:_SUMMARY_SNIPPET_MAX] + "..."
        lines.append(f"{msg.role}: {snippet}")
    if not lines:
        return ""
    conversation_text = "\n".join(lines)
    if system_prompt is None:
        system_prompt = _DEFAULT_SUMMARY_SYSTEM_ZH if language == "zh" else _DEFAULT_SUMMARY_SYSTEM_EN
    user_content = (_USER_INTRO_ZH if language == "zh" else _USER_INTRO_EN).format(
        conversation=conversation_text
    )
    from dare_framework.model import ModelInput

    sys_msg = Message(role="system", kind="summary", text=system_prompt)
    user_msg = Message(role="user", text=user_content)
    model_input = ModelInput(
        messages=[sys_msg, user_msg],
        tools=[],
        metadata={"compression": "moving_llm_summary"},
    )
    response = await model.generate(model_input)
    return (response.content or "").strip()


# ---------------------------------------------------------------------------
# 可挂载到 Context 的压缩器对象
# ---------------------------------------------------------------------------


class MovingCompressor:
    """移动窗口式 STM 压缩器，需在构造时挂载 model；压缩时对丢弃部分调用 LLM 做摘要并写回。

    用法（由 Builder 在创建 Context 时一并注入 LLM）：
        compressor = MovingCompressor(model=model)
        context = SmartContext(..., moving_compressor=compressor)
        assembled = await context.assemble_for_model()
    """

    def __init__(
        self,
        model: IModelAdapter,
        *,
        max_history_share: float = 0.5,
        parts: int = 2,
        tool_pair_safe: bool = True,
    ) -> None:
        if model is None:
            raise ValueError("MovingCompressor requires a non-null model")
        self._model = model
        self._max_history_share = max(0.01, min(1.0, float(max_history_share)))
        self._parts = max(1, int(parts))
        self._tool_pair_safe = bool(tool_pair_safe)

    @property
    def model(self) -> IModelAdapter | None:
        return self._model

    @property
    def max_history_share(self) -> float:
        return self._max_history_share

    @property
    def parts(self) -> int:
        return self._parts

    @property
    def tool_pair_safe(self) -> bool:
        return self._tool_pair_safe

    def _resolve_max_context_tokens(
        self, context: IContext, max_context_tokens: int | None
    ) -> int | None:
        """Resolve max context tokens for compression.

        语义约定：
        - 仅当调用方显式传入 max_context_tokens 时启用压缩；
        - 不再从 Budget.max_tokens 推导上下文窗口大小，避免将「计费预算」与
          「单次请求上下文长度」混用。
        """
        if max_context_tokens is None:
            return None
        if max_context_tokens <= 0:
            return None
        return max(1, int(max_context_tokens))

    async def prune(
        self,
        context: IContext,
        *,
        max_context_tokens: int | None = None,
        system_prompt: str | None = None,
        language: str = "zh",
    ) -> Dict[str, Any]:
        """按 token 预算裁剪 STM，对丢弃的消息调用 LLM 做摘要，将「一条摘要 + 保留消息」写回。"""
        resolved = self._resolve_max_context_tokens(context, max_context_tokens)
        stm_get = getattr(context, "stm_get", None)
        if not callable(stm_get) or resolved is None or resolved <= 0:
            return _empty_result()

        messages: List[Message] = list(stm_get())
        if not messages:
            return _empty_result()

        try:
            share = float(self._max_history_share)
        except (TypeError, ValueError):
            share = 0.5
        if share <= 0:
            share = 0.5
        budget_tokens = max(1, int(resolved * share))

        kept_messages, dropped_messages, stats = _compute_prune_result(
            messages,
            budget_tokens,
            parts=self._parts,
            tool_pair_safe=self._tool_pair_safe,
        )

        if dropped_messages:
            summary_text = await _summarize_messages_to_text(
                dropped_messages,
                self._model,
                system_prompt=system_prompt,
                language=language,
            )
            if summary_text:
                summary_message = Message(
                    role="system",
                    kind="summary",
                    text=summary_text,
                    metadata={"compressed": True, "strategy": "moving_llm_summary"},
                )
                _write_stm(context, [summary_message] + kept_messages)
                stats["summary_generated"] = True
                stats["summary_tokens"] = _estimate_tokens([summary_message])
            else:
                _write_stm(context, kept_messages)
                stats["summary_generated"] = False
        else:
            _write_stm(context, kept_messages)
            stats["summary_generated"] = False

        return stats


def _empty_result() -> Dict[str, Any]:
    return {
        "messages": [],
        "dropped_messages": [],
        "dropped_chunks": 0,
        "dropped_messages_count": 0,
        "dropped_tokens": 0,
        "kept_tokens": 0,
        "budget_tokens": 0,
        "summary_generated": False,
    }


__all__ = ["MovingCompressor"]
