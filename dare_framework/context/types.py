"""context domain types (context-centric).

Alignment note:
- Context holds references (STM/LTM/Knowledge + Budget).
- Messages are assembled request-time via `Context.assemble(...)`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """Unified message format."""

    role: str
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Budget:
    """Resource budget = limits + usage tracking."""

    # Limits
    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None

    # Usage tracking
    used_tokens: float = 0.0
    used_cost: float = 0.0
    used_time_seconds: float = 0.0
    used_tool_calls: int = 0


@dataclass
class AssembledContext:
    """Request-time context for a single LLM call."""

    messages: list[Message]
    tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["AssembledContext", "Budget", "Message"]
