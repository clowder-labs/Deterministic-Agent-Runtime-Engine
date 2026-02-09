"""context domain stable interfaces.

This domain defines the context-centric contract used as architecture evidence:
- Retrieval references live on Context (STM/LTM/Knowledge).
- `assemble()` constructs request-time (messages + tools + metadata).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dare_framework.config import Config
from dare_framework.context.types import AssembledContext, Budget, Message
from dare_framework.model import Prompt
from dare_framework.skill import Skill
from dare_framework.tool import CapabilityDescriptor


class IRetrievalContext(ABC):
    """Unified retrieval interface implemented by memory/knowledge."""

    @abstractmethod
    def get(self, query: str = "", **kwargs: Any) -> list[Message]: ...


class IContext(ABC):
    """Context interface - core context entity (context-centric)."""

    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def budget(self) -> Budget: ...

    @property
    @abstractmethod
    def short_term_memory(self) -> IRetrievalContext: ...

    @property
    @abstractmethod
    def long_term_memory(self) -> IRetrievalContext: ...

    @property
    @abstractmethod
    def knowledge(self) -> IRetrievalContext: ...

    @property
    @abstractmethod
    def config(self) -> Config: ...

    @property
    @abstractmethod
    def sys_prompt(self) -> Prompt: ...

    @property
    @abstractmethod
    def sys_skill(self) -> Skill | None:
        """
        用于将skill作为系统prompt的场景
        """
        ...

    # Short-term memory

    @abstractmethod
    def stm_add(self, message: Message) -> None: ...

    @abstractmethod
    def stm_get(self) -> list[Message]: ...

    @abstractmethod
    def stm_clear(self) -> list[Message]: ...

    # Budget methods

    @abstractmethod
    def budget_use(self, resource: str, amount: float) -> None: ...

    @abstractmethod
    def budget_check(self) -> None: ...

    @abstractmethod
    def budget_remaining(self, resource: str) -> float: ...

    # Tool listing (for ModelInput.tools)

    # Assembly (core)

    @abstractmethod
    def list_tools(self) -> list[CapabilityDescriptor]: ...

    def assemble(self) -> AssembledContext: ...

    # Compress (core)

    def compress(self, **options: Any) -> None: ...


class IAssembleContext(ABC):
    """
    Concrete implementation of AssembledContext.
    """

    @abstractmethod
    def assemble(self, context: IContext) -> AssembledContext: ...


__all__ = ["IContext", "IRetrievalContext", "IAssembleContext"]
