"""Default BaseAgent implementation (interface-aligned)."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from dare_framework.plan.types import RunResult, Task
from dare_framework.transport.types import TransportEnvelope, new_envelope_id

if TYPE_CHECKING:
    from dare_framework.agent._internal.builder import DareAgentBuilder, ReactAgentBuilder, SimpleChatAgentBuilder
    from dare_framework.transport.kernel import AgentChannel


class BaseAgent(ABC):
    """Abstract base class for all agent implementations.

    Provides common interface for agent execution.
    """

    def __init__(self, name: str, *, agent_channel: AgentChannel | None = None) -> None:
        """Initialize base agent.

        Args:
            name: Agent name identifier.
            agent_channel: Optional transport channel for streaming outputs.
        """
        self._name = name
        self._agent_channel = agent_channel
        self._active_transport: AgentChannel | None = None
        self._loop_task: asyncio.Task[None] | None = None
        self._logger = logging.getLogger("dare.agent")

    @property
    def name(self) -> str:
        """Agent name."""
        return self._name

    @property
    def agent_channel(self) -> AgentChannel | None:
        """Optional transport channel attached to the agent."""
        return self._agent_channel

    async def __call__(self, message: str | Task, deps: Any | None = None) -> RunResult:
        """Invoke the agent directly (no transport attached)."""
        return await self.run(message, deps=deps, transport=None)

    async def start(self) -> None:
        """Start agent components and spawn the transport loop."""
        channel = self._agent_channel
        if channel is None:
            return
        if self._loop_task is not None and not self._loop_task.done():
            return
        await channel.start()
        self._loop_task = asyncio.create_task(self.execute())

    async def stop(self) -> None:
        """Stop agent components and cancel the transport loop."""
        loop_task = self._loop_task
        self._loop_task = None
        if loop_task is not None:
            loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await loop_task
        if self._agent_channel is not None:
            await self._agent_channel.stop()

    async def execute(self) -> None:
        """Run the transport-driven loop for this agent (invoked by start)."""
        channel = self._agent_channel
        if channel is None:
            raise RuntimeError("Agent has no transport channel configured")
        await channel.start()
        while True:
            envelope = await channel.poll()
            if envelope.kind == "control":
                if envelope.type == "interrupt":
                    channel.interrupt()
                    continue
                if envelope.type in {"stop", "close"}:
                    await channel.stop()
                    break
            payload = envelope.payload
            if isinstance(payload, Task):
                task = payload
            elif isinstance(payload, str):
                task = payload
            else:
                continue
            try:
                await self.run(task, transport=channel)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._logger.exception("agent execute loop failed")

    async def run(
        self,
        task: str | Task,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Run a task and return a structured RunResult.

        Args:
            task: Task description or Task object.
            deps: Optional dependencies (currently unused).
            transport: Optional transport for streaming outputs.

        Returns:
            RunResult with output content.
        """
        task_description = task.description if isinstance(task, Task) else task
        previous = self._active_transport
        self._active_transport = transport
        try:
            output = await self._execute(task_description)
            result = RunResult(success=True, output=output)
            await self._send_transport_result(result, task=task_description, transport=transport)
            return result
        finally:
            self._active_transport = previous

    @abstractmethod
    async def _execute(self, task: str) -> str:
        """Execute task - must be implemented by subclasses.

        Args:
            task: Task description to execute.

        Returns:
            Model response as string.
        """
        ...

    async def _send_transport_result(
        self,
        result: RunResult,
        *,
        task: str | None = None,
        transport: AgentChannel | None = None,
    ) -> None:
        channel = transport
        if channel is None:
            return
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind="data",
            type="result",
            payload=result.output,
            meta={
                "success": result.success,
                "errors": list(result.errors),
                "task": task,
            },
        )
        try:
            await channel.send(envelope)
        except Exception:
            self._logger.exception("agent transport send failed")

    @staticmethod
    def simple_chat_agent_builder(name: str) -> SimpleChatAgentBuilder:
        """Return a builder for SimpleChatAgent."""
        from dare_framework.agent._internal.builder import SimpleChatAgentBuilder

        return SimpleChatAgentBuilder(name)

    @staticmethod
    def react_agent_builder(name: str) -> ReactAgentBuilder:
        """Return a builder for ReactAgent (ReAct tool loop)."""
        from dare_framework.agent._internal.builder import ReactAgentBuilder

        return ReactAgentBuilder(name)

    @staticmethod
    def five_layer_agent_builder(name: str) -> DareAgentBuilder:
        """Return a builder for DareAgent (five-layer orchestration)."""
        from dare_framework.agent._internal.builder import DareAgentBuilder

        return DareAgentBuilder(name)


__all__ = ["BaseAgent"]
