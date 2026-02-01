"""Component identity contracts shared across domains."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable


class ComponentType(Enum):
    """Component category taxonomy used for configuration scoping."""

    PLANNER = "planner"
    VALIDATOR = "validator"
    REMEDIATOR = "remediator"
    MEMORY = "memory"
    MODEL_ADAPTER = "model_adapter"
    TOOL = "tool"
    SKILL = "skill"
    MCP = "mcp"
    HOOK = "hook"
    PROMPT = "prompt"
    TELEMETRY = "telemetry"


@runtime_checkable
class IComponent(Protocol):
    """Cross-domain component identity contract.

    This contract exists so configuration and orchestration code can treat all pluggable
    components uniformly for enable/disable and per-component configuration lookups.
    """

    @property
    def name(self) -> str:
        """Stable name used for config lookups."""
        ...

    @property
    def component_type(self) -> ComponentType:
        """Component category used for config scoping."""
        ...


__all__ = ["ComponentType", "IComponent"]
