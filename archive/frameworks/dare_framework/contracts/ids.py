"""ID helpers used across the framework."""

from __future__ import annotations

from uuid import uuid4


def generator_id(prefix: str) -> str:
    """Generate a stable, prefixed identifier suitable for logs and evidence."""

    return f"{prefix}_{uuid4().hex}"

