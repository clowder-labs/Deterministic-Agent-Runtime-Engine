from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


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


class ICapabilityProvider(Protocol):
    """Provides capabilities to the Kernel tool gateway (Layer 2/1 integration)."""

    async def list(self) -> list[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object: ...

