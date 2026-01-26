from unittest.mock import MagicMock, patch

import pytest

pytest.skip(
    "Legacy stdout hook implementation is archived; port to canonical dare_framework once "
    "hook implementations exist.",
    allow_module_level=True,
)

from dare_framework.execution.impl.hooks.stdout import StdoutHook


def test_stdout_hook_renders_plan_validated():
    hook = StdoutHook()
    payload = {
        "event_type": "plan.validated",
        "payload": {"plan_description": "Test Plan"},
    }

    with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
        hook(payload)
        # Check if print was called with the expected string
        # print() appends a newline by default, so we check for exact match or startswith
        calls = [call.args[0] for call in mock_stdout.write.call_args_list if call.args[0] != "\n"]
        assert any(" [DARE:PLAN] Test Plan" in f" {c}" for c in calls)


def test_stdout_hook_renders_model_response():
    hook = StdoutHook()
    payload = {
        "event_type": "model.response",
        "payload": {
            "content": "Thinking...",
            "tool_calls": [{"name": "test_tool", "arguments": '{"arg": 1}'}],
        },
    }

    with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
        hook(payload)
        output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
        assert "[DARE:MODEL] Thinking..." in output
        assert "[DARE:TOOL_CALL] test_tool" in output


def test_stdout_hook_renders_tool_result():
    hook = StdoutHook()
    payload = {
        "event_type": "tool.result",
        "payload": {"capability_id": "test_tool", "success": True},
    }

    with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
        hook(payload)
        output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
        assert "[DARE:TOOL_RESULT] test_tool -> SUCCESS" in output
