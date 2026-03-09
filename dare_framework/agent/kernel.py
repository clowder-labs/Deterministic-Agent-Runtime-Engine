"""agent domain stable interfaces.

Alignment note:
- The minimal runtime surface is `IAgent.__call__(...)` (orchestration is an agent concern).

Design Decision (2026-03-09):
    The public agent input boundary accepts canonical user input only:

    - **Preferred**: Pass a `Message` for all rich-media and structured input.
    - **Convenience**: Pass a `str` for simple text prompts; the runtime will
      normalize it into `Message(role=user, kind=chat, text=...)`.

    `Task` remains an internal orchestration object and is no longer part of the
    public runtime contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from dare_framework.agent.status import AgentStatus
from dare_framework.context import Message
from dare_framework.plan.types import RunResult

if TYPE_CHECKING:
    from dare_framework.transport.kernel import AgentChannel


class IAgent(ABC):
    """Framework minimal runtime surface.

    This is the single entry point for executing tasks with an agent.
    The interface supports multiple execution modes through a unified API:

    Execution Modes:
        1. **Simple Mode** (str input, no tools):
           Agent generates a response using only the model.
        
        2. **ReAct Mode** (str input, with tools):
           Agent uses tools in a reasoning loop without explicit planning.
        
        3. **Five-Layer Mode** (internal orchestration from canonical Message):
           Full orchestration with Session → Milestone → Plan → Execute → Tool loops.

    Example:
        # Simple string input (auto-routed based on agent config)
        result = await agent("Explain this codebase")

        result = await agent(Message(role="user", text="Implement feature X"))
    """

    @abstractmethod
    async def __call__(
        self,
        message: str | Message,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Invoke the agent directly.

        If no transport is provided, implementations may route through a no-op
        transport to keep the execution pipeline consistent.
        """
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        """Start agent components and spawn the transport loop if configured."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """Stop agent components and cancel the transport loop."""
        raise NotImplementedError

    @abstractmethod
    def interrupt(self) -> None:
        """Interrupt current in-flight execution if supported."""
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> dict[str, Any]:
        """Pause execution if supported by the concrete agent."""
        raise NotImplementedError

    @abstractmethod
    def retry(self) -> dict[str, Any]:
        """Retry the last execution step if supported."""
        raise NotImplementedError

    @abstractmethod
    def reverse(self) -> dict[str, Any]:
        """Rollback/reverse execution if supported."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> AgentStatus:
        """Return current lifecycle status."""
        raise NotImplementedError


__all__ = ["IAgent"]
