"""Observability helpers for token estimation and context stats."""

from __future__ import annotations

from typing import Iterable

from dare_framework.context.types import Message


def estimate_tokens(text: str) -> int:
    """Estimate token count using a simple 4-chars-per-token heuristic."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def summarize_messages(messages: Iterable[Message]) -> dict[str, int]:
    """Summarize message content length for context metrics."""
    total_chars = 0
    total_bytes = 0
    total_tokens = 0
    count = 0
    for message in messages:
        count += 1
        content = message.content or ""
        total_chars += len(content)
        total_bytes += len(content.encode("utf-8"))
        total_tokens += estimate_tokens(content)
    return {
        "messages_count": count,
        "length_chars": total_chars,
        "length_bytes": total_bytes,
        "tokens_estimate": total_tokens,
    }


__all__ = ["estimate_tokens", "summarize_messages"]
