"""Core context compression helpers.

所有与“如何压缩上下文”相关的逻辑都集中在这里。

分层设计：
- `compress_context(...)`: 同步、低成本策略（截断 / 去重 / 启发式摘要），不直接调 LLM；
- `compress_context_llm_summary(...)`: 异步、高级策略，真正调用模型做语义摘要。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Tuple

from dare_framework.context.types import Message as CtxMessage
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
    # 未提供 max_messages 时，不做任何压缩（由调用方决定是否传入）。
    if max_messages is None or max_messages < 0:
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

    # strategy 默认为 "truncate"，后续可扩展更多策略。
    strategy = options.get("strategy", "truncate")

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
        removed_total += len(messages) - max_messages
        messages = messages[-max_messages:]

    # 如无任何压缩，不改写 STM，避免无意义写操作。
    if removed_total == 0:
        return

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
