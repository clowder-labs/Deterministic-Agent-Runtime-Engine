"""Core context compression helpers.

This module preserves the synchronous compression entrypoints described by the
design docs while the moving-window compressor remains available for
`assemble_for_model()` flows.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, List, Tuple

from dare_framework.context.types import Message as CtxMessage, MessageKind, MessageMark
from dare_framework.model import ModelInput

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.context.types import Message
    from dare_framework.model import IModelAdapter


_UNCHANGED = object()


def _freeze_value(value: Any) -> Any:
    """Build a hashable structural key for nested message payloads."""
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        frozen_items = [_freeze_value(item) for item in value]
        return tuple(sorted(frozen_items, key=repr))
    if is_dataclass(value) and not isinstance(value, type):
        return ("dataclass", type(value).__qualname__, _freeze_value(asdict(value)))
    if hasattr(value, "kind") and hasattr(value, "uri"):
        return (
            getattr(value.kind, "value", value.kind),
            value.uri,
            value.mime_type,
            value.filename,
            _freeze_value(getattr(value, "metadata", {})),
        )
    try:
        hash(value)
    except TypeError:
        if hasattr(value, "__dict__"):
            return (type(value).__qualname__, _freeze_value(vars(value)))
        return (type(value).__qualname__, repr(value))
    return value


def _copy_message(
    message: Message,
    *,
    data: dict[str, Any] | None | object = _UNCHANGED,
    metadata: dict[str, Any] | object = _UNCHANGED,
) -> Message:
    return CtxMessage(
        role=message.role,
        kind=message.kind,
        text=message.text,
        attachments=list(message.attachments),
        data=message.data if data is _UNCHANGED else data,
        name=message.name,
        metadata=message.metadata if metadata is _UNCHANGED else dict(metadata),
        mark=getattr(message, "mark", MessageMark.TEMPORARY),
        id=getattr(message, "id", None),
    )


def _dedup_messages(messages: List[Message]) -> Tuple[List[Message], int]:
    """De-duplicate only when the full public message payload matches."""
    seen: set[Any] = set()
    result: List[Message] = []
    removed = 0

    for msg in messages:
        key = (
            msg.role,
            msg.kind,
            msg.text,
            msg.name,
            _freeze_value(msg.attachments),
            _freeze_value(msg.data),
        )
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        result.append(msg)

    return result, removed


def _build_summary_preview(
    messages: List[Message],
    max_messages: int,
    tail_max: int = 10,
) -> Tuple[List[Message], int]:
    """Heuristic, model-free summary strategy."""
    total = len(messages)
    if total <= max_messages or max_messages <= 1:
        return messages, 0

    tail_capacity = max_messages - 1
    keep_tail = min(tail_max, tail_capacity, total)
    head = messages[:-keep_tail] if keep_tail > 0 else messages
    tail = messages[-keep_tail:] if keep_tail > 0 else []

    if not head:
        return messages, 0

    preview_lines: List[str] = []
    for msg in head:
        content = (msg.text or "").strip()
        if not content:
            continue
        snippet = content.replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:120] + "..."
        preview_lines.append(f"{msg.role}: {snippet}")

    if not preview_lines:
        return messages, 0

    summary_text = "Conversation summary (heuristic, no LLM):\n" + "\n".join(preview_lines)
    summary_message = CtxMessage(
        role="system",
        kind=MessageKind.SUMMARY,
        text=summary_text,
        metadata={"compressed": True, "strategy": "summary_preview"},
    )

    new_messages: List[Message] = [summary_message, *tail]
    removed = total - len(new_messages)
    return new_messages, removed


def _estimate_tokens(messages: List[Message]) -> int:
    """Rough token estimate using a cheap character + attachment heuristic."""
    total = 0
    for msg in messages:
        content = (msg.text or "").strip()
        attachment_tokens = len(msg.attachments) * 32
        total += max(1, len(content) // 4) + attachment_tokens + 8
    return total


def _trim_to_target_tokens(messages: List[Message], target_tokens: int | None) -> Tuple[List[Message], int]:
    """Trim oldest messages until estimated token size fits target_tokens."""
    if target_tokens is None or target_tokens <= 0:
        return messages, 0
    if _estimate_tokens(messages) <= target_tokens:
        return messages, 0

    trimmed = list(messages)
    removed = 0
    while len(trimmed) > 1 and _estimate_tokens(trimmed) > target_tokens:
        removable_idx = next(
            (
                idx
                for idx, message in enumerate(trimmed)
                if getattr(message, "mark", MessageMark.TEMPORARY)
                not in (MessageMark.IMMUTABLE, MessageMark.PERSISTENT)
            ),
            None,
        )
        if removable_idx is None:
            break
        trimmed.pop(removable_idx)
        removed += 1
    return trimmed, removed


def _extract_tool_call_ids(message: Message) -> list[str]:
    """Collect tool call ids declared on an assistant message."""
    if message.role != "assistant":
        return []
    tool_calls = message.data.get("tool_calls", []) if isinstance(message.data, dict) else []
    if not isinstance(tool_calls, list):
        return []

    ids: list[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        tool_id = call.get("id")
        if isinstance(tool_id, str) and tool_id.strip():
            ids.append(tool_id.strip())
    return ids


def _enforce_tool_pair_safety(messages: List[Message]) -> Tuple[List[Message], int]:
    """Keep tool_call/tool_result in sync so compression never leaves orphan pairs."""
    tool_result_ids = {
        message.name.strip()
        for message in messages
        if message.role == "tool" and isinstance(message.name, str) and message.name.strip()
    }

    updated_messages: list[Message] = []
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

        filtered_calls = []
        for call in raw_calls:
            if not isinstance(call, dict):
                continue
            tool_id = call.get("id")
            if isinstance(tool_id, str) and tool_id.strip() and tool_id.strip() in tool_result_ids:
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
            updated_data = dict(message.data) if isinstance(message.data, dict) else {}
            updated_data["tool_calls"] = filtered_calls
            updated_messages.append(_copy_message(message, data=updated_data))
        else:
            retained_call_ids.update(_extract_tool_call_ids(message))
            updated_messages.append(message)

    final_messages: list[Message] = []
    for message in updated_messages:
        if message.role == "tool":
            tool_id = message.name.strip() if isinstance(message.name, str) else ""
            if tool_id in retained_call_ids or (tool_id and tool_id in retained_idless_tool_names):
                final_messages.append(message)
                continue
            if tool_id:
                changes += 1
                continue
        final_messages.append(message)
    return final_messages, changes


def _annotate_strategy(messages: List[Message], strategy: str) -> List[Message]:
    """Attach strategy metadata to the first message when compression rewrites context."""
    if not messages:
        return messages
    for message in messages:
        if message.metadata.get("compressed") is True:
            return messages

    head = messages[0]
    metadata = dict(head.metadata)
    metadata["compressed"] = True
    metadata.setdefault("strategy", strategy)
    messages[0] = _copy_message(head, metadata=metadata)
    return messages


def compress_context(
    context: IContext,
    *,
    phase: str | None = None,
    max_messages: int | None = None,
    **options: Any,
) -> None:
    """Compress short-term memory for a given context."""
    _ = phase

    target_tokens_raw = options.get("target_tokens")
    target_tokens: int | None = None
    if target_tokens_raw is not None:
        try:
            target_tokens = int(target_tokens_raw)
        except (TypeError, ValueError):
            target_tokens = None

    if (max_messages is None or max_messages < 0) and (target_tokens is None or target_tokens <= 0):
        return

    stm_get = getattr(context, "stm_get", None)
    stm_clear = getattr(context, "stm_clear", None)
    stm_add = getattr(context, "stm_add", None)
    if not callable(stm_get) or not callable(stm_clear) or not callable(stm_add):
        return

    messages: List[Message] = list(stm_get())
    if not messages:
        return

    if max_messages is None:
        max_messages = len(messages)
    elif max_messages < 0:
        max_messages = len(messages)

    strategy = options.get("strategy", "truncate")
    tool_pair_safe = bool(options.get("tool_pair_safe", False))

    removed_total = 0

    if strategy == "summary_preview":
        messages, removed = _build_summary_preview(messages, max_messages)
        removed_total += removed

    if strategy == "dedup_then_truncate":
        messages, removed = _dedup_messages(messages)
        removed_total += removed

    if max_messages == 0:
        removed_total += len(messages)
        messages = []
    elif len(messages) > max_messages:
        protected = [
            message
            for message in messages
            if getattr(message, "mark", MessageMark.TEMPORARY)
            in (MessageMark.IMMUTABLE, MessageMark.PERSISTENT)
        ]
        temporary = [
            message
            for message in messages
            if getattr(message, "mark", MessageMark.TEMPORARY)
            not in (MessageMark.IMMUTABLE, MessageMark.PERSISTENT)
        ]
        keep_temporary = max(max_messages - len(protected), 0)
        if keep_temporary <= 0:
            kept_tail: list[Message] = []
        elif keep_temporary < len(temporary):
            kept_tail = temporary[-keep_temporary:]
        else:
            kept_tail = temporary
        kept_tail_refs = {id(message) for message in kept_tail}
        messages = [
            message
            for message in messages
            if (
                getattr(message, "mark", MessageMark.TEMPORARY)
                in (MessageMark.IMMUTABLE, MessageMark.PERSISTENT)
            )
            or id(message) in kept_tail_refs
        ]
        removed_total += len(protected) + len(temporary) - len(messages)

    messages, removed = _trim_to_target_tokens(messages, target_tokens)
    removed_total += removed

    if tool_pair_safe:
        messages, changes = _enforce_tool_pair_safety(messages)
        removed_total += changes

    if removed_total == 0:
        return

    messages = _annotate_strategy(messages, str(strategy))
    stm_clear()
    for msg in messages:
        stm_add(msg)


async def compress_context_llm_summary(
    context: IContext,
    *,
    model: IModelAdapter,
    max_messages: int,
    keep_tail: int = 8,
    system_prompt: str | None = None,
    language: str = "zh",
) -> None:
    """High-level compression using the LLM to generate a semantic summary."""
    if max_messages <= 1:
        return

    stm_get = getattr(context, "stm_get", None)
    stm_clear = getattr(context, "stm_clear", None)
    stm_add = getattr(context, "stm_add", None)
    if not callable(stm_get) or not callable(stm_clear) or not callable(stm_add):
        return

    messages: List[Message] = list(stm_get())
    total = len(messages)
    if total <= max_messages:
        return

    tail_capacity = max_messages - 1
    keep_tail_eff = min(keep_tail, tail_capacity, total)
    head = messages[:-keep_tail_eff] if keep_tail_eff > 0 else messages
    tail = messages[-keep_tail_eff:] if keep_tail_eff > 0 else []

    if not head:
        return

    lines: List[str] = []
    for msg in head:
        content = (msg.text or "").strip()
        if not content:
            continue
        snippet = content.replace("\n", " ")
        if len(snippet) > 512:
            snippet = snippet[:512] + "..."
        lines.append(f"{msg.role}: {snippet}")

    if not lines:
        return

    conversation_text = "\n".join(lines)
    if system_prompt is None:
        if language == "zh":
            system_prompt = (
                "你是一个对话摘要助手，请在不丢失关键信息的前提下，"
                "用简洁、结构化的方式总结下面的一段历史对话。"
                "可以合并重复信息，但不要编造不存在的内容。"
            )
        else:
            system_prompt = (
                "You are a conversation summarization assistant. "
                "Produce a concise, structured summary of the following history, "
                "preserving key facts and decisions. Do not invent new information."
            )

    sys_msg = CtxMessage(role="system", kind=MessageKind.SUMMARY, text=system_prompt)
    user_intro = (
        "下面是一段需要被压缩的历史对话，请输出一个摘要，用于后续继续对话使用。\n\n"
        "=== 历史开始 ===\n"
        f"{conversation_text}\n"
        "=== 历史结束 ==="
        if language == "zh"
        else
        "Here is the conversation history that needs to be compressed. "
        "Please output a summary that can be used for continuing the dialogue.\n\n"
        "=== HISTORY START ===\n"
        f"{conversation_text}\n"
        "=== HISTORY END ==="
    )
    user_msg = CtxMessage(role="user", text=user_intro)

    model_input = ModelInput(
        messages=[sys_msg, user_msg],
        tools=[],
        metadata={"compression": "llm_summary"},
    )

    response = await model.generate(model_input)
    summary_text = (response.content or "").strip()
    if not summary_text:
        return

    summary_message = CtxMessage(
        role="system",
        kind=MessageKind.SUMMARY,
        text=summary_text,
        metadata={"compressed": True, "strategy": "llm_summary"},
    )

    stm_clear()
    stm_add(summary_message)
    for msg in tail:
        stm_add(msg)


__all__ = ["compress_context", "compress_context_llm_summary"]
