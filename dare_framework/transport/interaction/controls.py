"""Stable runtime control identifiers for transport-driven sessions."""

from __future__ import annotations

from enum import StrEnum


class AgentControl(StrEnum):
    """Built-in runtime control signals.

    These signals are deterministic and MUST NOT be interpreted as natural language prompts.
    """

    INTERRUPT = "interrupt"
    PAUSE = "pause"
    RETRY = "retry"
    REVERSE = "reverse"

    @classmethod
    def value_of(cls, raw: str) -> AgentControl | None:
        """Resolve control id to enum value without raising."""
        normalized = raw.strip()
        if not normalized:
            return None
        try:
            return cls(normalized)
        except ValueError:
            return None

    @classmethod
    def valueOf(cls, raw: str) -> AgentControl | None:
        """Backwards-compatible alias for callers using camelCase naming."""
        return cls.value_of(raw)


__all__ = ["AgentControl"]
