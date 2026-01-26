"""Kernel tool models (v2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.tool import ToolDefinition, ToolResult, ToolType


class CapabilityType(Enum):
    """Canonical capability types (v2.0)."""

    TOOL = "tool"
    AGENT = "agent"
    UI = "ui"


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Canonical description of an invokable capability (v2.0)."""

    id: str
    type: CapabilityType
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


__all__ = [
    "CapabilityType",
    "CapabilityDescriptor",
    "RiskLevel",
    "ToolDefinition",
    "ToolResult",
    "ToolType",
]
