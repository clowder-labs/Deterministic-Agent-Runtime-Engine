from __future__ import annotations

from dare_framework.compression.core import compress_context
from dare_framework.config import Config
from dare_framework.context import Context, Message, MessageMark


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


def test_compress_context_tool_pair_safe_keeps_idless_tool_context() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="assistant",
            content="tool call without id",
            metadata={"tool_calls": [{"name": "demo_tool", "arguments": {"x": 1}}]},
        )
    )
    ctx.stm_add(Message(role="tool", name="demo_tool", content='{"success": true}'))

    compress_context(ctx, strategy="truncate", max_messages=10, tool_pair_safe=True)

    messages = ctx.stm_get()
    assistant_message = next(message for message in messages if message.role == "assistant")
    raw_calls = assistant_message.metadata.get("tool_calls", [])
    assert isinstance(raw_calls, list)
    assert len(raw_calls) == 1
    assert any(message.role == "tool" and message.name == "demo_tool" for message in messages)


def test_compress_context_tool_pair_safe_drops_orphan_tool_results_with_mixed_id_modes() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="assistant",
            content="mixed tool calls",
            metadata={
                "tool_calls": [
                    {"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}},
                    {"name": "demo_tool", "arguments": {"x": 2}},
                ]
            },
        )
    )
    ctx.stm_add(Message(role="tool", name="tc_1", content='{"success": true}'))
    ctx.stm_add(Message(role="tool", name="demo_tool", content='{"success": true}'))
    ctx.stm_add(Message(role="tool", name="tc_orphan", content='{"success": true}'))

    compress_context(ctx, strategy="truncate", max_messages=10, tool_pair_safe=True)

    tool_names = [message.name for message in ctx.stm_get() if message.role == "tool"]
    assert "tc_1" in tool_names
    assert "demo_tool" in tool_names
    assert "tc_orphan" not in tool_names


def test_compress_context_tool_pair_safe_preserves_assistant_id_and_mark_when_filtering_calls() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="assistant",
            content="mixed tool calls",
            id="assistant-state",
            mark=MessageMark.PERSISTENT,
            metadata={
                "tool_calls": [
                    {"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}},
                    {"id": "tc_missing", "name": "demo_tool", "arguments": {"x": 2}},
                ]
            },
        )
    )
    ctx.stm_add(Message(role="tool", name="tc_1", content='{"success": true}'))

    compress_context(ctx, strategy="truncate", max_messages=10, tool_pair_safe=True)

    assistant_message = next(message for message in ctx.stm_get() if message.role == "assistant")
    assert assistant_message.id == "assistant-state"
    assert assistant_message.mark == MessageMark.PERSISTENT
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


def test_compress_context_negative_max_messages_keeps_unbounded_semantics() -> None:
    ctx = Context(config=Config())
    for idx in range(4):
        ctx.stm_add(Message(role="user", content=f"msg-{idx}"))

    before_messages = list(ctx.stm_get())
    compress_context(
        ctx,
        strategy="truncate",
        max_messages=-1,
        target_tokens=10_000,
    )
    after_messages = ctx.stm_get()

    assert [message.content for message in after_messages] == [
        message.content for message in before_messages
    ]


def test_compress_context_annotate_preserves_message_identity_fields() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="assistant",
            content="keep identity",
            id="assistant-1",
            mark=MessageMark.PERSISTENT,
        )
    )
    ctx.stm_add(Message(role="user", content="latest"))

    compress_context(ctx, strategy="dedup_then_truncate", max_messages=1, phase="pre_tool")

    head = ctx.stm_get()[0]
    assert head.id == "assistant-1"
    assert head.mark == MessageMark.PERSISTENT
    assert head.metadata.get("compressed") is True
    assert head.metadata.get("strategy") == "dedup_then_truncate"


def test_compress_context_max_messages_preserves_protected_marks() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="system",
            content="immutable",
            id="imm-1",
            mark=MessageMark.IMMUTABLE,
        )
    )
    ctx.stm_add(
        Message(
            role="assistant",
            content="persistent",
            id="persist-1",
            mark=MessageMark.PERSISTENT,
        )
    )
    for idx in range(4):
        ctx.stm_add(Message(role="user", content=f"temp-{idx}", id=f"tmp-{idx}"))

    compress_context(ctx, strategy="truncate", max_messages=3, target_tokens=10_000)

    messages = ctx.stm_get()
    ids = [message.id for message in messages]
    assert "imm-1" in ids
    assert "persist-1" in ids
    assert len(messages) == 3
