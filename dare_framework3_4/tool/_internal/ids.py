"""ID helpers for tool evidence and tracing."""

from __future__ import annotations

from uuid import uuid4


def generate_id(prefix: str) -> str:
    """Generate a stable ID with a prefix."""
    return f"{prefix}_{uuid4().hex}"


__all__ = ["generate_id"]
