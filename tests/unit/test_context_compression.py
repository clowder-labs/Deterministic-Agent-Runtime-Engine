from __future__ import annotations

from dare_framework.compression.core import compress_context
from dare_framework.config import Config
from dare_framework.context import Context, Message


def _tool_ids(message: Message) -> list[str]:
    raw_calls = message.metadata.get("tool_calls", [])
    if not isinstance(raw_calls, list):
        return []
    ids: list[str] = []
    for item in raw_calls:
        if not isinstance(item, dict):
            continue
        tool_id = item.get("id")
        if isinstance(tool_id, str) and tool_id:
            ids.append(tool_id)
    return ids


def test_compress_context_tool_pair_safe_removes_orphan_tool_result() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="assistant",
            content="tool call",
            metadata={"tool_calls": [{"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}}]},
        )
    )
    ctx.stm_add(Message(role="tool", name="tc_1", content='{"success": true}'))
    ctx.stm_add(Message(role="tool", name="tc_orphan", content='{"success": true}'))

    compress_context(ctx, strategy="truncate", max_messages=10, tool_pair_safe=True)

    messages = ctx.stm_get()
    tool_names = [message.name for message in messages if message.role == "tool"]
    assert "tc_1" in tool_names
    assert "tc_orphan" not in tool_names


def test_compress_context_tool_pair_safe_removes_unmatched_tool_call_ids() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="assistant",
            content="tool call",
            metadata={
                "tool_calls": [
                    {"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}},
                    {"id": "tc_2", "name": "missing_tool", "arguments": {"x": 2}},
                ]
            },
        )
    )
    ctx.stm_add(Message(role="tool", name="tc_1", content='{"success": true}'))

    compress_context(ctx, strategy="truncate", max_messages=10, tool_pair_safe=True)

    assistant_message = next(message for message in ctx.stm_get() if message.role == "assistant")
    assert _tool_ids(assistant_message) == ["tc_1"]


def test_compress_context_target_tokens_trims_long_history() -> None:
    ctx = Context(config=Config())
    for idx in range(8):
        ctx.stm_add(Message(role="user", content=f"long-message-{idx}-" + "x" * 120))

    before_count = len(ctx.stm_get())
    compress_context(ctx, strategy="truncate", max_messages=8, target_tokens=80)
    after_messages = ctx.stm_get()

    assert len(after_messages) < before_count
    assert len(after_messages) >= 1
