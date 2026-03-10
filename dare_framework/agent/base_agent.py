"""Default BaseAgent implementation (interface-aligned)."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import contextlib
from contextvars import ContextVar
from dataclasses import replace
import logging
from typing import TYPE_CHECKING, Any

from dare_framework.agent._internal.input_normalizer import coerce_user_message, preview_text
from dare_framework.agent._internal.output_normalizer import normalize_run_output
from dare_framework.agent.interfaces import IAgentOrchestration
from dare_framework.agent.kernel import IAgent
from dare_framework.agent.status import AgentStatus
from dare_framework.context import Message, MessageKind, MessageRole
from dare_framework.plan.types import RunResult
from dare_framework.transport.types import (
    EnvelopeKind,
    MessagePayload,
    TransportEnvelope,
    new_envelope_id,
)

if TYPE_CHECKING:
    from dare_framework.agent.builder import DareAgentBuilder, ReactAgentBuilder, SimpleChatAgentBuilder
    from dare_framework.transport.kernel import AgentChannel


class BaseAgent(IAgent, IAgentOrchestration, ABC):
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

    async def __call__(
        self,
        message: str | Message,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Invoke the agent directly."""
        _ = deps
        resolved_transport = transport if transport is not None else _NO_OP_AGENT_CHANNEL
        canonical_message = coerce_user_message(message)
        result = await self.execute(canonical_message, transport=resolved_transport)
        return self._with_normalized_output_text(result)

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
        try:
            while self._status == AgentStatus.RUNNING:
                try:
                    polled = await channel.poll()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self._logger.exception("agent channel poll failed")
                    break

                try:
                    envelopes = _coerce_polled_envelopes(polled)
                except Exception:
                    self._logger.exception("agent channel poll returned invalid envelope payload")
                    continue

                for envelope in envelopes:
                    if self._status != AgentStatus.RUNNING:
                        break
                    if envelope.kind != EnvelopeKind.MESSAGE:
                        await _send_transport_error(
                            channel=channel,
                            envelope_id=envelope.id,
                            target="envelope",
                            code="UNSUPPORTED_ENVELOPE_KIND",
                            reason=f"unsupported envelope kind for agent queue: {envelope.kind.value!r}",
                        )
                        continue
                    task = _coerce_transport_prompt(envelope.payload)
                    if task is None:
                        await _send_transport_error(
                            channel=channel,
                            envelope_id=envelope.id,
                            target="prompt",
                            code="INVALID_MESSAGE_PAYLOAD",
                            reason="invalid message payload (expected MessagePayload)",
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

                    self._in_flight_task = asyncio.create_task(
                        self._execute_polled_message(
                            task,
                            channel=channel,
                            envelope_id=envelope.id,
                        ),
                    )
                    try:
                        await self._in_flight_task
                    except asyncio.CancelledError:
                        # Cancelled (typically via interrupt) is expected.
                        pass
                    except Exception as exc:
                        reason = str(exc).strip() or exc.__class__.__name__
                        await _send_transport_error(
                            channel=channel,
                            envelope_id=envelope.id,
                            target="prompt",
                            code="AGENT_EXECUTION_FAILED",
                            reason=reason,
                        )
                        self._logger.exception("agent interaction handler failed")
                    finally:
                        self._in_flight_task = None
        finally:
            self._loop_task = None

    async def _start_components(self) -> None:
        """Hook for subclasses to start internal components."""

    async def _stop_components(self) -> None:
        """Hook for subclasses to stop internal components."""

    async def _execute_polled_message(
        self,
        task: Message,
        *,
        channel: AgentChannel,
        envelope_id: str | None,
    ) -> None:
        """Execute one polled message and send response envelope through channel."""
        # Keep transport-loop execution state task-local so concurrent execute() calls on
        # the same agent instance do not leak loop state across tasks.
        transport_loop_token = _TRANSPORT_LOOP_EXECUTION_CTX.set(True)
        try:
            result = await self.execute(task, transport=channel)
        finally:
            _TRANSPORT_LOOP_EXECUTION_CTX.reset(transport_loop_token)
        result = self._with_normalized_output_text(result)
        await self._send_transport_result(
            result,
            task=preview_text(task),
            transport=channel,
            reply_to=envelope_id,
        )

    def _is_transport_loop_execution(self, *, transport: AgentChannel | None) -> bool:
        """Return whether execute() is currently running under the transport loop."""
        return bool(transport is not None and _TRANSPORT_LOOP_EXECUTION_CTX.get())

    def _with_normalized_output_text(self, result: RunResult) -> RunResult:
        """Ensure RunResult.output_text is filled for downstream consumers."""
        if result.output_text is not None:
            return result
        return replace(result, output_text=normalize_run_output(result.output))

    @abstractmethod
    async def execute(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute task - must be implemented by subclasses.

        Args:
            task: Task description to execute.
            transport: Transport channel bound to this execution.

        Returns:
            Normalized run result.
        """
        ...

    async def _send_transport_result(
        self,
        result: RunResult,
        *,
        task: str | None = None,
        transport: AgentChannel | None = None,
        reply_to: str | None = None,
    ) -> None:
        channel = transport
        if channel is None:
            return
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            reply_to=reply_to,
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id=new_envelope_id(),
                role="assistant",
                message_kind="chat",
                text=result.output_text or "",
                data={
                    "success": result.success,
                    "output": result.output,
                    "errors": list(result.errors),
                    "task": task,
                },
            ),
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


class _NoOpAgentChannel:
    """AgentChannel no-op implementation for direct execution path."""

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> TransportEnvelope:
        raise RuntimeError("NoOpAgentChannel does not support polling")

    async def send(self, msg: TransportEnvelope) -> None:
        _ = msg

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> None:
        return None

    def get_agent_control_handler(self) -> None:
        return None


_NO_OP_AGENT_CHANNEL = _NoOpAgentChannel()
_TRANSPORT_LOOP_EXECUTION_CTX: ContextVar[bool] = ContextVar("_transport_loop_execution", default=False)


def _coerce_polled_envelopes(polled: Any) -> list[TransportEnvelope]:
    if isinstance(polled, TransportEnvelope):
        return [polled]
    if isinstance(polled, list):
        envelopes: list[TransportEnvelope] = []
        for envelope in polled:
            if not isinstance(envelope, TransportEnvelope):
                raise TypeError(f"invalid envelope type in batch poll: {type(envelope).__name__}")
            envelopes.append(envelope)
        return envelopes
    raise TypeError(f"invalid poll return type: {type(polled).__name__}")


def _coerce_transport_prompt(payload: Any) -> Message | None:
    """Normalize transport message payloads into canonical Message input."""
    if isinstance(payload, MessagePayload):
        if payload.message_kind is not MessageKind.CHAT:
            return None
        if payload.role is not MessageRole.USER:
            return None
        return Message(
            id=payload.id,
            role=MessageRole.USER,
            kind=MessageKind.CHAT,
            text=payload.text,
            attachments=list(payload.attachments),
            data=dict(payload.data) if isinstance(payload.data, dict) else None,
            metadata=dict(payload.metadata),
        )
    return None


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
                payload=MessagePayload(
                    id=new_envelope_id(),
                    role="assistant",
                    message_kind="summary",
                    text=reason,
                    data={
                        "success": False,
                        "target": target,
                        "code": code,
                        "reason": reason,
                    },
                ),
            )
        )
    except Exception:
        logging.getLogger("dare.agent").exception("agent error envelope send failed")
