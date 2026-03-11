"""Guidance-domain deterministic action handler."""

from __future__ import annotations

from typing import Any

from dare_framework.guidance.guidance_queue import GuidanceItem, GuidanceQueue
from dare_framework.transport.interaction.handlers import IActionHandler
from dare_framework.transport.interaction.resource_action import ResourceAction


class GuidanceActionHandler(IActionHandler):
    """Handle deterministic guidance-domain actions (inject / list / clear)."""

    def __init__(self, guidance_queue: GuidanceQueue) -> None:
        self._queue = guidance_queue

    def supports(self) -> set[ResourceAction]:
        return {
            ResourceAction.GUIDE_INJECT,
            ResourceAction.GUIDE_LIST,
            ResourceAction.GUIDE_CLEAR,
        }

    # noinspection PyMethodOverriding
    async def invoke(
        self,
        action: ResourceAction,
        **params: Any,
    ) -> Any:
        if action == ResourceAction.GUIDE_INJECT:
            content = params.get("content")
            if not content or not str(content).strip():
                raise ValueError("guide:inject requires a non-empty 'content' parameter")
            item = self._queue.enqueue(str(content))
            return {
                "id": item.id,
                "pending_count": self._queue.pending_count,
            }

        if action == ResourceAction.GUIDE_LIST:
            items = self._queue.peek_all()
            return {
                "items": [_item_to_dict(i) for i in items],
                "count": len(items),
            }

        if action == ResourceAction.GUIDE_CLEAR:
            removed = self._queue.clear()
            return {"removed": removed}

        raise ValueError(f"unsupported guidance action: {action.value}")


def _item_to_dict(item: GuidanceItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "content": item.content,
        "created_at": item.created_at,
    }


__all__ = ["GuidanceActionHandler"]
