"""Execution context passed to capability implementations (v2).

The Kernel stays protocol-agnostic and does not prescribe a specific tool context
shape. For the current Python implementation, tools receive a small `RunContext`
object derived from the running session/milestone IDs plus optional dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

DepsT = TypeVar("DepsT")


@dataclass
class RunContext(Generic[DepsT]):
    """A minimal tool execution context (intentionally small, serializable fields)."""

    deps: DepsT | None
    run_id: str
    task_id: str | None = None
    milestone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    config: Any | None = None

