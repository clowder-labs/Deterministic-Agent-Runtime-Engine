"""Tool domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework.contracts.tool import ITool
from dare_framework.tool.types import CapabilityDescriptor
from dare_framework.tool.impl.skills.protocols import ISkill


class ICapabilityProvider(Protocol):
    """Provides capabilities to the Kernel tool gateway."""

    async def list(self) -> list[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object: ...


__all__ = ["ITool", "ISkill", "ICapabilityProvider"]
