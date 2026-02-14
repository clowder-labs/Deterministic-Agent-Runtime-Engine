from __future__ import annotations

import json

from dare_framework.context.types import Message
from dare_framework.model.adapters.openrouter_adapter import _serialize_messages


def test_serialize_messages_preserves_assistant_tool_calls() -> None:
    messages = [
        Message(role="user", content="Need a filename"),
        Message(
            role="assistant",
            content="I need your confirmation first.",
            metadata={
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "ask_user",
                        "arguments": {
                            "questions": [
                                {
                                    "header": "Target",
                                    "question": "Pick a file name",
                                    "options": [
                                        {"label": "a.txt", "description": "A"},
                                        {"label": "b.txt", "description": "B"},
                                    ],
                                }
                            ]
                        },
                    }
                ]
            },
        ),
        Message(
            role="tool",
            name="call_1",
            content=json.dumps(
                {
                    "success": True,
                    "output": {"answers": {"Pick a file name": "a.txt"}},
                },
                ensure_ascii=False,
            ),
        ),
    ]

    serialized = _serialize_messages(messages)

    assistant_payload = serialized[1]
    assert "tool_calls" in assistant_payload
    tool_call = assistant_payload["tool_calls"][0]
    assert tool_call["id"] == "call_1"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "ask_user"
    assert isinstance(tool_call["function"]["arguments"], str)
    assert serialized[2]["tool_call_id"] == "call_1"
