import pytest

from dare_framework.transport.interaction.control_handler import AgentControlHandler
from dare_framework.transport.interaction.controls import AgentControl


def test_agent_control_value_of_returns_enum_when_valid() -> None:
    assert AgentControl.value_of("interrupt") == AgentControl.INTERRUPT
    assert AgentControl.value_of(" pause ") == AgentControl.PAUSE


def test_agent_control_value_of_returns_none_when_invalid() -> None:
    assert AgentControl.value_of("") is None
    assert AgentControl.value_of("unknown") is None
    assert AgentControl.value_of("start") is None
    assert AgentControl.value_of("stop") is None


class _FakeLifecycle:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.interrupted = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    def interrupt(self):
        self.interrupted = True
        return {"ok": True}

    def pause(self):
        return {"ok": True}

    def retry(self):
        return {"ok": True}

    def reverse(self):
        return {"ok": True}

    def get_status(self) -> str:
        return "running"


@pytest.mark.asyncio
async def test_control_handler_invokes_runtime_controls_not_lifecycle_start_stop() -> None:
    lifecycle = _FakeLifecycle()
    handler = AgentControlHandler(lifecycle)

    result = await handler.invoke(AgentControl.INTERRUPT)

    assert result["ok"] is True
    assert lifecycle.interrupted is True
    assert lifecycle.started is False
    assert lifecycle.stopped is False
