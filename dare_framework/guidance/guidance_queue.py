"""Thread-safe guidance queue with consume-on-drain semantics."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class GuidanceItem:
    """Single guidance entry enqueued by the user."""

    id: str
    content: str
    created_at: float


class GuidanceQueue:
    """FIFO queue for in-flight user guidance messages.

    The queue is written to by ``GuidanceActionHandler`` (via ``enqueue``) and
    drained by ``Context.assemble()`` (via ``drain_all_sync``).  A
    ``threading.Lock`` is used so that ``drain_all_sync`` can be called from
    the synchronous ``assemble()`` method.
    """

    def __init__(self, *, max_size: int = 100) -> None:
        self._items: deque[GuidanceItem] = deque()
        self._lock = threading.Lock()
        self._max_size = max_size

    # ------------------------------------------------------------------
    # Write side (called from async action handler → GIL-safe)
    # ------------------------------------------------------------------

    def enqueue(self, content: str) -> GuidanceItem:
        """Append a guidance message.  Returns the created item for auditing.

        Raises ``ValueError`` if *content* is empty or whitespace-only, or if
        the queue has reached *max_size*.
        """
        if not content or not content.strip():
            raise ValueError("guidance content must be a non-empty string")
        item = GuidanceItem(
            id=str(uuid.uuid4()),
            content=content,
            created_at=time.time(),
        )
        with self._lock:
            if len(self._items) >= self._max_size:
                raise RuntimeError(
                    f"guidance queue full ({self._max_size} items); "
                    "drain or clear before enqueuing more"
                )
            self._items.append(item)
        return item

    # ------------------------------------------------------------------
    # Read / consume side
    # ------------------------------------------------------------------

    def drain_all_sync(self) -> list[GuidanceItem]:
        """Pop **all** pending items atomically.

        This is the only consumption path — called from the synchronous
        ``Context.assemble()`` method.  After this call the queue is empty.
        """
        with self._lock:
            items = list(self._items)
            self._items.clear()
        return items

    def peek_all(self) -> list[GuidanceItem]:
        """Return a snapshot of pending items without consuming them."""
        with self._lock:
            return list(self._items)

    def clear(self) -> int:
        """Remove all pending items.  Returns the number removed."""
        with self._lock:
            count = len(self._items)
            self._items.clear()
        return count

    @property
    def pending_count(self) -> int:
        """Number of pending guidance items (lock-free; approximate)."""
        return len(self._items)


__all__ = ["GuidanceItem", "GuidanceQueue"]
