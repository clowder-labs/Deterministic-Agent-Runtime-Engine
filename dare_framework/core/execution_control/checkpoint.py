from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Checkpoint:
    """Checkpoint metadata aligned to the v2.0 architecture doc.

    The checkpoint payload/storage is implementation-defined; this canonical type captures
    the minimum information needed to align checkpoints with the EventLog for replay/audit.
    """

    id: str
    created_at: float
    event_id: str
    snapshot_ref: str | None = None
    note: str | None = None
