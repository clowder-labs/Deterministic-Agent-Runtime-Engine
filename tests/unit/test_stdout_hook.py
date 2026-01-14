import pytest

from dare_framework.components.hooks.stdout import StdoutHook
from dare_framework.core.models.event import Event


@pytest.mark.asyncio
async def test_stdout_hook_renders_tool_invoke(capsys):
    hook = StdoutHook()
    event = Event(event_type="tool.invoke", payload={"tool": "run_command", "args": {"cmd": "ls"}})

    await hook.on_event(event)

    output = capsys.readouterr().out
    assert "[tool.invoke]" in output
    assert "run_command" in output
    assert "cmd" in output


@pytest.mark.asyncio
async def test_stdout_hook_renders_model_response(capsys):
    hook = StdoutHook()
    event = Event(
        event_type="model.response",
        payload={"content": "ok", "tool_calls": [{"name": "run_command", "arguments": {}}]},
    )

    await hook.on_event(event)

    output = capsys.readouterr().out
    assert "[model]" in output
    assert "ok" in output
    assert "[model.tools]" in output
    assert "run_command" in output
