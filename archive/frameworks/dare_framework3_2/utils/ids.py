"""ID generation helpers used across the framework."""

from __future__ import annotations

from uuid import uuid4


def generate_id(prefix: str) -> str:
    """Generate a stable, prefixed identifier suitable for logs and evidence.
    
    Args:
        prefix: A short string prefix (e.g., "task", "step", "evidence")
    
    Returns:
        A unique identifier in the format "{prefix}_{uuid_hex}"
    """
    return f"{prefix}_{uuid4().hex}"
