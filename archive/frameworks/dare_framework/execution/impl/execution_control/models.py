"""Kernel execution control models (v2)."""

from __future__ import annotations

from enum import Enum


class ExecutionSignal(Enum):
    """Signals used by the Kernel to pause/cancel or request HITL (v2.0)."""

    NONE = "none"
    PAUSE_REQUESTED = "pause_requested"
    CANCEL_REQUESTED = "cancel_requested"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"

