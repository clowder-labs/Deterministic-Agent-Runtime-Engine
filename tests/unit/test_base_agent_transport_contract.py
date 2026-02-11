from __future__ import annotations

import asyncio
from typing import Any

import pytest

from dare_framework.agent.base_agent import BaseAgent
from dare_framework.agent.status import AgentStatus
from dare_framework.transport import EnvelopeKind, TransportEnvelope


class _CaptureAgent(BaseAgent):
    def __init__(self, name: str, *, agent_channel: Any | None = None) -> None:
        super().__init__(name, agent_channel=agent_channel)
        self.seen_transport: Any | None = None
        self.seen_tasks: list[str] = []

    async def execute(self, task: str | Any, *, transport: Any = None) -> str:
        task_text = task.description if hasattr(task, "description") else str(task)
        self.seen_transport = transport
        self.seen_tasks.append(task_text)
        if len(self.seen_tasks) >= 2:
            self._status = AgentStatus.STOPPED
        return f"ok:{task_text}"


class _BatchPollingChannel:
    def __init__(self) -> None:
        self._sent: list[TransportEnvelope] = []
        self._polled = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> list[TransportEnvelope]:
        if self._polled:
            await asyncio.sleep(10)
            return []
        self._polled = True
        return [
            TransportEnvelope(id="m1", kind=EnvelopeKind.MESSAGE, payload="first"),
            TransportEnvelope(id="m2", kind=EnvelopeKind.MESSAGE, payload="second"),
        ]

    async def send(self, msg: TransportEnvelope) -> None:
        self._sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


class _RecordingSendChannel:
    def __init__(self) -> None:
        self.sent: list[TransportEnvelope] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> TransportEnvelope:
        raise RuntimeError("not used")

    async def send(self, msg: TransportEnvelope) -> None:
        self.sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


@pytest.mark.asyncio
async def test_public_surface_uses_call_not_run() -> None:
    agent = _CaptureAgent("capture-agent")
    assert not hasattr(agent, "run")
    assert hasattr(agent, "execute")


@pytest.mark.asyncio
async def test_call_with_no_transport_injects_noop_transport() -> None:
    agent = _CaptureAgent("capture-agent")

    result = await agent("hello")

    assert result.success is True
    assert agent.seen_transport is not None


@pytest.mark.asyncio
async def test_call_path_does_not_send_terminal_response_to_transport() -> None:
    agent = _CaptureAgent("capture-agent")
    transport = _RecordingSendChannel()

    result = await agent("hello", transport=transport)

    assert result.success is True
    assert transport.sent == []


@pytest.mark.asyncio
async def test_transport_loop_accepts_batched_messages_from_poll() -> None:
    channel = _BatchPollingChannel()
    agent = _CaptureAgent("batch-agent", agent_channel=channel)
    agent._status = AgentStatus.RUNNING

    await agent._run_transport_loop()

    assert agent.seen_tasks == ["first", "second"]
    assert len(channel._sent) == 2
