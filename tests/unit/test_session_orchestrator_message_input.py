from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from dare_framework.agent._internal.session_orchestrator import run_session_loop
from dare_framework.context import AttachmentRef, Message, MessageKind, MessageRole
from dare_framework.plan.types import RunResult, Task


class _CaptureContext:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def stm_add(self, message: Message) -> None:
        self.messages.append(message)

    def budget_check(self) -> None:
        return None


class _SessionLoopProbeAgent:
    def __init__(self) -> None:
        self._context = _CaptureContext()
        self._session_state = None
        self._planner = None
        self._exec_ctl = None
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def _emit_hook(self, phase: Any, payload: dict[str, Any]) -> None:
        _ = (phase, payload)

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, dict(payload)))

    async def _run_milestone_loop(self, milestone: Any, *, transport: Any | None = None) -> Any:
        _ = (milestone, transport)
        return SimpleNamespace(success=True, outputs=["done"], errors=[])

    def _poll_or_raise(self) -> None:
        return None

    def _log(self, message: str) -> None:
        _ = message

    def _budget_stats(self) -> dict[str, Any]:
        return {}


@pytest.mark.asyncio
async def test_run_session_loop_prefers_task_input_message_over_description() -> None:
    agent = _SessionLoopProbeAgent()
    task = Task(
        description="fallback description",
        input_message=Message(
            role=MessageRole.USER,
            kind=MessageKind.CHAT,
            text="actual user text",
            attachments=[AttachmentRef(uri="https://example.com/a.png")],
        ),
    )

    result = await run_session_loop(agent, task)

    assert result.success is True
    assert len(agent._context.messages) == 1
    user_message = agent._context.messages[0]
    assert user_message.text == "actual user text"
    assert len(user_message.attachments) == 1
    assert user_message.attachments[0].uri == "https://example.com/a.png"
