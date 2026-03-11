"""Unit tests for GuidanceQueue."""
from __future__ import annotations

import pytest

from dare_framework.guidance.guidance_queue import GuidanceItem, GuidanceQueue


def test_enqueue_and_drain_returns_items_in_order() -> None:
    queue = GuidanceQueue()
    queue.enqueue("first")
    queue.enqueue("second")
    queue.enqueue("third")

    items = queue.drain_all_sync()
    assert len(items) == 3
    assert items[0].content == "first"
    assert items[1].content == "second"
    assert items[2].content == "third"
    # Each item has a unique id
    ids = {item.id for item in items}
    assert len(ids) == 3


def test_drain_empties_queue() -> None:
    queue = GuidanceQueue()
    queue.enqueue("hello")
    assert queue.pending_count == 1

    items = queue.drain_all_sync()
    assert len(items) == 1
    assert queue.pending_count == 0

    # Second drain returns empty
    items2 = queue.drain_all_sync()
    assert items2 == []


def test_peek_does_not_consume() -> None:
    queue = GuidanceQueue()
    queue.enqueue("peek me")

    peeked = queue.peek_all()
    assert len(peeked) == 1
    assert peeked[0].content == "peek me"

    # peek again — still there
    peeked2 = queue.peek_all()
    assert len(peeked2) == 1

    # drain still gets the item
    drained = queue.drain_all_sync()
    assert len(drained) == 1
    assert drained[0].content == "peek me"


def test_clear_removes_all() -> None:
    queue = GuidanceQueue()
    queue.enqueue("a")
    queue.enqueue("b")
    assert queue.pending_count == 2

    removed = queue.clear()
    assert removed == 2
    assert queue.pending_count == 0

    # drain returns empty after clear
    assert queue.drain_all_sync() == []


def test_empty_queue_drain_returns_empty_list() -> None:
    queue = GuidanceQueue()
    assert queue.drain_all_sync() == []
    assert queue.pending_count == 0


def test_enqueue_rejects_empty_content() -> None:
    queue = GuidanceQueue()
    with pytest.raises(ValueError, match="non-empty"):
        queue.enqueue("")
    with pytest.raises(ValueError, match="non-empty"):
        queue.enqueue("   ")


def test_enqueue_respects_max_size() -> None:
    queue = GuidanceQueue(max_size=2)
    queue.enqueue("one")
    queue.enqueue("two")
    with pytest.raises(RuntimeError, match="queue full"):
        queue.enqueue("three")

    # After drain, can enqueue again
    queue.drain_all_sync()
    queue.enqueue("four")
    assert queue.pending_count == 1


def test_item_has_created_at_timestamp() -> None:
    queue = GuidanceQueue()
    item = queue.enqueue("timestamped")
    assert isinstance(item, GuidanceItem)
    assert item.created_at > 0
