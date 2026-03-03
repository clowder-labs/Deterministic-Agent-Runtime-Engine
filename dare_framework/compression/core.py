"""Core context compression helpers.

所有与“如何压缩上下文”相关的逻辑都集中在这里。

分层设计：
- `compress_context(...)`: 同步、低成本策略（截断 / 去重 / 启发式摘要），不直接调 LLM；
- `compress_context_llm_summary(...)`: 异步、高级策略，真正调用模型做语义摘要。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Tuple

from dare_framework.context.types import Message as CtxMessage, MessageMark
from dare_framework.model import ModelInput

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.context.types import Message
    from dare_framework.model import IModelAdapter


def _dedup_messages(messages: List[Message]) -> Tuple[List[Message], int]:
    """Lightweight de-duplication on (role, content).

    保留首次出现的 `(role, content)` 组合，后续完全相同的消息视为冗余并移除。
    不考虑 metadata/name 差异，保持实现简单且性能可接受。
    """
    seen: set[int] = set()
    result: List[Message] = []
    removed = 0

    for msg in messages:
        key = (msg.role, msg.content)
        h = hash(key)
        if h in seen:
            removed += 1
            continue
        seen.add(h)
        result.append(msg)

    return result, removed


def _build_summary_preview(
    messages: List[Message],
    max_messages: int,
    tail_max: int = 10,
) -> Tuple[List[Message], int]:
    """Heuristic, model-free summary strategy.

    - 将较早的历史折叠为一条 system 消息（对话预览）；
    - 保留最近若干条原始消息，整体条数不超过 max_messages。
    """
    total = len(messages)
    if total <= max_messages or max_messages <= 1:
        # 不需要折叠，或压缩空间不足以容纳“摘要 + 至少 1 条原始消息”
        return messages, 0

    # 预留尾部原始消息的容量：至多 tail_max 条，且整体不超过 max_messages - 1（给摘要预留 1）
    tail_capacity = max_messages - 1
    keep_tail = min(tail_max, tail_capacity, total)
    head = messages[:-keep_tail] if keep_tail > 0 else messages
    tail = messages[-keep_tail:] if keep_tail > 0 else []

    if not head:
        # 所有消息都在“尾部”，不需要再折叠
        return messages, 0

    preview_lines: List[str] = []
    for msg in head:
        content = (msg.content or "").strip()
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
        content=summary_text,
        metadata={"compressed": True, "strategy": "summary_preview"},
    )

    new_messages: List[Message] = [summary_message, *tail]
    removed = total - len(new_messages)
    return new_messages, removed


def _estimate_tokens(messages: List[Message]) -> int:
    """Rough token estimate using a cheap character-based heuristic."""
    total = 0
    for msg in messages:
        content = (msg.content or "").strip()
        total += max(1, len(content) // 4) + 8
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
            # Nothing removable left (all protected by mark semantics).
            break
        trimmed.pop(removable_idx)
        removed += 1
    return trimmed, removed


def _extract_tool_call_ids(message: Message) -> list[str]:
    """Collect tool call ids declared on an assistant message."""
    if message.role != "assistant":
        return []
    tool_calls = message.metadata.get("tool_calls", [])
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
        raw_calls = message.metadata.get("tool_calls", [])
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
                # Some providers emit tool calls without stable ids. Keep these calls and
                # retain matching tool results by tool name.
                filtered_calls.append(call)
                tool_name = call.get("name")
                if isinstance(tool_name, str) and tool_name.strip():
                    retained_idless_tool_names.add(tool_name.strip())

        if len(filtered_calls) != len(raw_calls):
            changes += len(raw_calls) - len(filtered_calls)
            metadata = dict(message.metadata)
            metadata["tool_calls"] = filtered_calls
            updated_messages.append(
                CtxMessage(
                    role=message.role,
                    content=message.content,
                    name=message.name,
                    metadata=metadata,
                    mark=getattr(message, "mark", MessageMark.TEMPORARY),
                    id=getattr(message, "id", None),
                )
            )
        else:
            retained_call_ids.update(_extract_tool_call_ids(message))
            updated_messages.append(message)

    final_messages: list[Message] = []
    for message in updated_messages:
        if message.role == "tool":
            tool_id = message.name.strip() if isinstance(message.name, str) else ""
            if tool_id in retained_call_ids:
                final_messages.append(message)
                continue
            if tool_id and tool_id in retained_idless_tool_names:
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
    messages[0] = CtxMessage(
        role=head.role,
        content=head.content,
        name=head.name,
        metadata=metadata,
        mark=getattr(head, "mark", MessageMark.TEMPORARY),
        id=getattr(head, "id", None),
    )
    return messages


def compress_context(
    context: IContext,
    *,
    phase: str | None = None,
    max_messages: int | None = None,
    **options: Any,
) -> None:
    """Compress short-term memory for a given context.

    调用约定：
    - 当前版本关注“核心算法”，不区分不同 phase 的差异化策略；
    - Agent / 上层代码在需要时显式传入 max_messages 和 strategy。

    当前实现：
    - 支持两种轻量策略（通过 options['strategy'] 选择，默认 "truncate"）：
      - "truncate": 仅按条数截断，保留最近 max_messages 条；
      - "dedup_then_truncate": 先按 (role, content) 轻量去重，再按条数截断。
      - "summary_preview": 将较早历史折叠为一条 system 摘要消息 + 若干尾部原始消息。

    NOTE:
        - phase 参数暂未参与决策，仅为未来差异化调用预留。
    """
    # 未提供任何压缩上限时，不做压缩（由调用方决定是否传入）。
    target_tokens_raw = options.get("target_tokens")
    target_tokens: int | None = None
    if target_tokens_raw is not None:
        try:
            target_tokens = int(target_tokens_raw)
        except (TypeError, ValueError):
            target_tokens = None

    if (max_messages is None or max_messages < 0) and (target_tokens is None or target_tokens <= 0):
        return

    # 通过 IContext 的标准接口访问 STM，避免绑定具体实现细节。
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
        # Keep historical sentinel semantics: negative means "no message cap".
        max_messages = len(messages)

    # strategy 默认为 "truncate"，后续可扩展更多策略。
    strategy = options.get("strategy", "truncate")
    tool_pair_safe = bool(options.get("tool_pair_safe", False))

    removed_total = 0

    # Step 1: 高级策略（摘要折叠）
    if strategy == "summary_preview":
        messages, removed = _build_summary_preview(messages, max_messages)
        removed_total += removed

    # Step 2: 去重（可选）
    if strategy == "dedup_then_truncate":
        messages, removed = _dedup_messages(messages)
        removed_total += removed

    # Step 3: 按条数截断（保留最新 max_messages 条）
    if max_messages == 0:
        # 明确传入 0 视为“清空 STM”
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
            kept_tail = []
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

    # Step 4: token-aware 截断（按估算 token 控制）
    messages, removed = _trim_to_target_tokens(messages, target_tokens)
    removed_total += removed

    # Step 5: 工具调用对齐保护（可选）
    if tool_pair_safe:
        messages, changes = _enforce_tool_pair_safety(messages)
        removed_total += changes

    # 如无任何压缩，不改写 STM，避免无意义写操作。
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
    """High-level compression using the LLM to generate a semantic summary.

    算法思路：
    - 若 STM 消息数未超过 max_messages，则直接返回；
    - 否则：
      - 保留最近 `keep_tail` 条原始消息（不超过 max_messages - 1）；
      - 把更早的消息作为“需要被摘要的部分”，构造一轮 summary prompt；
      - 调用模型生成摘要文本；
      - 将 STM 重写为：一条 system 摘要消息 + 若干尾部原始消息。
    """
    if max_messages <= 1:
        # 容量过小，暂不做摘要折叠，交给上层决定是否清空等策略。
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

    # 预留尾部原始消息
    tail_capacity = max_messages - 1
    keep_tail_eff = min(keep_tail, tail_capacity, total)
    head = messages[:-keep_tail_eff] if keep_tail_eff > 0 else messages
    tail = messages[-keep_tail_eff:] if keep_tail_eff > 0 else []

    if not head:
        return

    # 构造摘要输入文本：按行列出 role: content（适当截断）
    lines: List[str] = []
    for msg in head:
        content = (msg.content or "").strip()
        if not content:
            continue
        snippet = content.replace("\n", " ")
        if len(snippet) > 512:
            snippet = snippet[:512] + "..."
        lines.append(f"{msg.role}: {snippet}")

    if not lines:
        return

    conversation_text = "\n".join(lines)

    # 默认的 summary 指令（中英文都支持，主要偏中文）
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

    # 构造 ModelInput
    sys_msg = CtxMessage(role="system", content=system_prompt)
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
    user_msg = CtxMessage(role="user", content=user_intro)

    model_input = ModelInput(
        messages=[sys_msg, user_msg],
        tools=[],
        metadata={"compression": "llm_summary"},
    )

    # 调用模型生成摘要
    response = await model.generate(model_input)
    summary_text = (response.content or "").strip()
    if not summary_text:
        # 摘要失败时，不修改 STM，交由上层策略处理。
        return

    summary_message = CtxMessage(
        role="system",
        content=summary_text,
        metadata={"compressed": True, "strategy": "llm_summary"},
    )

    # 重写 STM：摘要 + 尾部原始消息
    stm_clear()
    stm_add(summary_message)
    for msg in tail:
        stm_add(msg)


__all__ = ["compress_context", "compress_context_llm_summary"]
