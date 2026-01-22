"""Tool domain types - minimal definitions for agent compatibility."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """A single evidence record suitable for auditing and verification."""

    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ToolResult:
    """Canonical tool invocation result, including evidence.

    Used for compatibility with 3.2 output format.
    """

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


__all__ = ["ToolResult", "Evidence"]
