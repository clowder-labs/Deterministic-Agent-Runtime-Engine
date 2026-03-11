"""Unit tests for guidance injection into Context.assemble()."""
from __future__ import annotations

from dare_framework.config import Config
from dare_framework.context.context import Context
from dare_framework.context.types import Message, MessageKind, MessageRole
from dare_framework.guidance.guidance_queue import GuidanceQueue


def _make_context(*, guidance_queue: GuidanceQueue | None = None) -> Context:
    return Context(id="test-ctx", config=Config(), guidance_queue=guidance_queue)


def test_guidance_injected_at_assemble_time() -> None:
    queue = GuidanceQueue()
    ctx = _make_context(guidance_queue=queue)
    ctx.stm_add(Message(role=MessageRole.USER, text="original task"))

    queue.enqueue("focus on error handling")

    assembled = ctx.assemble()
    texts = [m.text for m in assembled.messages]
    assert "original task" in texts
    assert "focus on error handling" in texts


def test_guidance_consumed_after_single_assemble() -> None:
    queue = GuidanceQueue()
    ctx = _make_context(guidance_queue=queue)
    queue.enqueue("one-shot guidance")

    assembled1 = ctx.assemble()
    assert any(m.text == "one-shot guidance" for m in assembled1.messages)

    # Second assemble has no NEW guidance (but old messages remain in STM)
    assembled2 = ctx.assemble()
    # The guidance message is still in STM (it was added by drain), but the queue is empty
    assert queue.pending_count == 0
    # Count guidance messages — should be exactly 1 (not 2)
    guidance_msgs = [m for m in assembled2.messages if m.metadata.get("source") == "user_guidance"]
    assert len(guidance_msgs) == 1


def test_no_guidance_original_behavior_unchanged() -> None:
    ctx = _make_context()  # no guidance_queue
    ctx.stm_add(Message(role=MessageRole.USER, text="hello"))

    assembled = ctx.assemble()
    assert len(assembled.messages) == 1
    assert assembled.messages[0].text == "hello"


def test_no_guidance_with_queue_original_behavior_unchanged() -> None:
    queue = GuidanceQueue()
    ctx = _make_context(guidance_queue=queue)
    ctx.stm_add(Message(role=MessageRole.USER, text="hello"))

    # No guidance enqueued — assemble should work normally
    assembled = ctx.assemble()
    assert len(assembled.messages) == 1
    assert assembled.messages[0].text == "hello"


def test_multiple_guidance_injected_in_order() -> None:
    queue = GuidanceQueue()
    ctx = _make_context(guidance_queue=queue)

    queue.enqueue("guidance A")
    queue.enqueue("guidance B")
    queue.enqueue("guidance C")

    assembled = ctx.assemble()
    guidance_msgs = [m for m in assembled.messages if m.metadata.get("source") == "user_guidance"]
    assert len(guidance_msgs) == 3
    assert guidance_msgs[0].text == "guidance A"
    assert guidance_msgs[1].text == "guidance B"
    assert guidance_msgs[2].text == "guidance C"


def test_guidance_message_has_user_role_and_metadata() -> None:
    queue = GuidanceQueue()
    ctx = _make_context(guidance_queue=queue)

    item = queue.enqueue("important guidance")

    assembled = ctx.assemble()
    guidance_msgs = [m for m in assembled.messages if m.metadata.get("source") == "user_guidance"]
    assert len(guidance_msgs) == 1

    msg = guidance_msgs[0]
    assert msg.role == MessageRole.USER
    assert msg.kind == MessageKind.CHAT
    assert msg.text == "important guidance"
    assert msg.metadata["guidance_id"] == item.id
    assert msg.metadata["source"] == "user_guidance"


def test_guidance_appears_after_existing_stm_messages() -> None:
    queue = GuidanceQueue()
    ctx = _make_context(guidance_queue=queue)
    ctx.stm_add(Message(role=MessageRole.USER, text="original"))

    queue.enqueue("correction")

    assembled = ctx.assemble()
    assert assembled.messages[0].text == "original"
    assert assembled.messages[1].text == "correction"
