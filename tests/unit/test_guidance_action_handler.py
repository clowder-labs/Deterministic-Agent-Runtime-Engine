"""Unit tests for GuidanceActionHandler."""
from __future__ import annotations

import pytest

from dare_framework.guidance.action_handler import GuidanceActionHandler
from dare_framework.guidance.guidance_queue import GuidanceQueue
from dare_framework.transport.interaction.resource_action import ResourceAction


@pytest.fixture
def queue() -> GuidanceQueue:
    return GuidanceQueue()


@pytest.fixture
def handler(queue: GuidanceQueue) -> GuidanceActionHandler:
    return GuidanceActionHandler(queue)


def test_supports_returns_all_three_actions(handler: GuidanceActionHandler) -> None:
    supported = handler.supports()
    assert supported == {
        ResourceAction.GUIDE_INJECT,
        ResourceAction.GUIDE_LIST,
        ResourceAction.GUIDE_CLEAR,
    }


@pytest.mark.asyncio
async def test_inject_enqueues_and_returns_id(handler: GuidanceActionHandler, queue: GuidanceQueue) -> None:
    result = await handler.invoke(ResourceAction.GUIDE_INJECT, content="focus on tests")
    assert "id" in result
    assert result["pending_count"] == 1
    assert queue.pending_count == 1

    # The queued item has the right content
    items = queue.peek_all()
    assert items[0].content == "focus on tests"
    assert items[0].id == result["id"]


@pytest.mark.asyncio
async def test_inject_missing_content_raises(handler: GuidanceActionHandler) -> None:
    with pytest.raises(ValueError, match="content"):
        await handler.invoke(ResourceAction.GUIDE_INJECT)

    with pytest.raises(ValueError, match="content"):
        await handler.invoke(ResourceAction.GUIDE_INJECT, content="")


@pytest.mark.asyncio
async def test_list_returns_pending_items(handler: GuidanceActionHandler) -> None:
    await handler.invoke(ResourceAction.GUIDE_INJECT, content="item A")
    await handler.invoke(ResourceAction.GUIDE_INJECT, content="item B")

    result = await handler.invoke(ResourceAction.GUIDE_LIST)
    assert result["count"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["content"] == "item A"
    assert result["items"][1]["content"] == "item B"


@pytest.mark.asyncio
async def test_clear_removes_all_pending(handler: GuidanceActionHandler, queue: GuidanceQueue) -> None:
    await handler.invoke(ResourceAction.GUIDE_INJECT, content="item 1")
    await handler.invoke(ResourceAction.GUIDE_INJECT, content="item 2")
    assert queue.pending_count == 2

    result = await handler.invoke(ResourceAction.GUIDE_CLEAR)
    assert result["removed"] == 2
    assert queue.pending_count == 0


@pytest.mark.asyncio
async def test_inject_list_clear_lifecycle(handler: GuidanceActionHandler) -> None:
    # Inject two items
    r1 = await handler.invoke(ResourceAction.GUIDE_INJECT, content="step 1")
    r2 = await handler.invoke(ResourceAction.GUIDE_INJECT, content="step 2")
    assert r2["pending_count"] == 2

    # List shows both
    listed = await handler.invoke(ResourceAction.GUIDE_LIST)
    assert listed["count"] == 2

    # Clear removes all
    cleared = await handler.invoke(ResourceAction.GUIDE_CLEAR)
    assert cleared["removed"] == 2

    # List is now empty
    listed2 = await handler.invoke(ResourceAction.GUIDE_LIST)
    assert listed2["count"] == 0
