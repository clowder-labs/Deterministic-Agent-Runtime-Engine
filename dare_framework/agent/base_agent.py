"""Default BaseAgent implementation (interface-aligned)."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from dare_framework.agent.kernel import IAgent
from dare_framework.agent.status import AgentStatus
from dare_framework.plan.types import RunResult, Task
from dare_framework.transport.interaction.payloads import build_error_payload, build_success_payload
from dare_framework.transport.types import EnvelopeKind, TransportEnvelope, new_envelope_id

if TYPE_CHECKING:
    from dare_framework.agent.builder import DareAgentBuilder, ReactAgentBuilder, SimpleChatAgentBuilder
    from dare_framework.transport.kernel import AgentChannel


class BaseAgent(IAgent, ABC):
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
        self._in_flight_task: asyncio.Task[None] | None = None
        self._started = False
        self._status = AgentStatus.INIT
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
        self._status = AgentStatus.STARTING
        if self._started:
            self._status = AgentStatus.RUNNING
            return
        try:
            await self._start_components()
            channel = self._agent_channel
            if channel is not None:
                # Builder-time wiring is required: channel must already have deterministic handlers.
                if channel.get_action_handler_dispatcher() is None or channel.get_agent_control_handler() is None:
                    raise RuntimeError(
                        "channel interaction handlers not configured: "
                        "action dispatcher and control handler are required before start"
                    )

                await channel.start()
                self._loop_task = asyncio.create_task(self._run_transport_loop())
            self._started = True
            self._status = AgentStatus.RUNNING
        except Exception:
            self._started = False
            self._status = AgentStatus.STOPPED
            raise

    async def stop(self) -> None:
        """Stop agent components and cancel the transport loop."""
        self._status = AgentStatus.STOPPING
        try:
            in_flight = self._in_flight_task
            self._in_flight_task = None
            if in_flight is not None and not in_flight.done():
                in_flight.cancel()
            loop_task = self._loop_task
            self._loop_task = None
            if loop_task is not None:
                loop_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await loop_task
            if self._agent_channel is not None:
                await self._agent_channel.stop()
            await self._stop_components()
        finally:
            self._started = False
            self._status = AgentStatus.STOPPED

    def get_status(self) -> AgentStatus:
        """Return current lifecycle status."""
        return self._status

    def interrupt(self) -> None:
        """Cancel the current in-flight operation if any.

        This is used by deterministic control handling (AgentControl=interrupt). The transport channel
        does not own execution tasks; the agent/dispatcher does.
        """
        task = self._in_flight_task
        if task is not None and not task.done():
            task.cancel()

    def pause(self) -> dict[str, Any]:
        """Default pause behavior for control handling."""
        return {"ok": False, "error": "pause not implemented"}

    def retry(self) -> dict[str, Any]:
        """Default retry behavior for control handling."""
        return {"ok": False, "error": "retry not implemented"}

    def reverse(self) -> dict[str, Any]:
        """Default reverse behavior for control handling."""
        return {"ok": False, "error": "reverse not implemented"}

    async def _run_transport_loop(self) -> None:
        """Run the transport-driven loop for this agent (invoked by start)."""
        channel = self._agent_channel
        if channel is None:
            raise RuntimeError("Agent has no transport channel configured")

        poll_task: asyncio.Task[TransportEnvelope] = asyncio.create_task(channel.poll())
        try:
            while self._status == AgentStatus.RUNNING:
                wait_set: set[asyncio.Task[Any]] = {poll_task}
                if self._in_flight_task is not None:
                    wait_set.add(self._in_flight_task)
                done, _pending = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED)

                completed_in_flight = self._in_flight_task if self._in_flight_task in done else None
                if completed_in_flight is not None:
                    try:
                        await completed_in_flight
                    except asyncio.CancelledError:
                        # Cancelled (typically via interrupt) is expected.
                        pass
                    except Exception:
                        self._logger.exception("agent interaction handler failed")
                    finally:
                        if self._in_flight_task is completed_in_flight:
                            self._in_flight_task = None

                if poll_task in done:
                    try:
                        envelope = poll_task.result()
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        self._logger.exception("agent channel poll failed")
                        break
                    poll_task = asyncio.create_task(channel.poll())

                    if envelope.kind != EnvelopeKind.MESSAGE:
                        await _send_transport_error(
                            channel=channel,
                            envelope_id=envelope.id,
                            target="envelope",
                            code="UNSUPPORTED_ENVELOPE_KIND",
                            reason=f"unsupported envelope kind for agent queue: {envelope.kind.value!r}",
                        )
                        continue

                    if self._in_flight_task is not None and not self._in_flight_task.done():
                        await _send_transport_error(
                            channel=channel,
                            envelope_id=envelope.id,
                            target="prompt",
                            code="AGENT_BUSY",
                            reason="agent is busy",
                        )
                        continue

                    # Channel handles ACTION/CONTROL and only MESSAGE reaches this queue.
                    self._in_flight_task = asyncio.create_task(
                        _dispatch_message(self, channel, envelope),
                    )
        finally:
            poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poll_task
            self._loop_task = None

    async def _start_components(self) -> None:
        """Hook for subclasses to start internal components."""

    async def _stop_components(self) -> None:
        """Hook for subclasses to stop internal components."""

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
            payload={
                **build_success_payload(
                    kind="message",
                    target="prompt",
                    resp={
                        "output": result.output,
                        "success": result.success,
                        "errors": list(result.errors),
                        "task": task,
                    },
                ),
                "output": result.output,
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
        from dare_framework.agent.builder import SimpleChatAgentBuilder

        return SimpleChatAgentBuilder(name)

    @staticmethod
    def react_agent_builder(name: str) -> ReactAgentBuilder:
        """Return a builder for ReactAgent (ReAct tool loop)."""
        from dare_framework.agent.builder import ReactAgentBuilder

        return ReactAgentBuilder(name)

    @staticmethod
    def dare_agent_builder(name: str) -> DareAgentBuilder:
        """Return a builder for DareAgent (five-layer orchestration)."""
        from dare_framework.agent.builder import DareAgentBuilder

        return DareAgentBuilder(name)


__all__ = ["BaseAgent"]


async def _dispatch_message(agent: BaseAgent, channel: AgentChannel, envelope: TransportEnvelope) -> None:
    payload = envelope.payload
    if not _is_prompt_payload(payload):
        await _send_transport_error(
            channel=channel,
            envelope_id=envelope.id,
            target="prompt",
            code="INVALID_MESSAGE_PAYLOAD",
            reason="invalid message payload (expected string prompt or Task)",
        )
        return
    await agent.run(payload, transport=channel)


def _is_prompt_payload(payload: Any) -> bool:
    if isinstance(payload, str):
        return True
    return hasattr(payload, "description") and payload.__class__.__name__ == "Task"


async def _send_transport_error(
    *,
    channel: AgentChannel,
    envelope_id: str | None,
    target: str,
    code: str,
    reason: str,
) -> None:
    try:
        await channel.send(
            TransportEnvelope(
                id=new_envelope_id(),
                kind=EnvelopeKind.MESSAGE,
                reply_to=envelope_id,
                payload=build_error_payload(
                    kind="message",
                    target=target,
                    code=code,
                    reason=reason,
                ),
            )
        )
    except Exception:
        logging.getLogger("dare.agent").exception("agent error envelope send failed")
