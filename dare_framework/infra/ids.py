"""Shared identifier helpers for internal use."""

from __future__ import annotations

import uuid


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


__all__ = ["generate_id"]
