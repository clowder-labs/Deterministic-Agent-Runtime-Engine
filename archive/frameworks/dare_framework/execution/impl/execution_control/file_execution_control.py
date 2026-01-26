from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import time
from uuid import uuid4

from dare_framework.execution.impl.event.protocols import IEventLog
from dare_framework.execution.impl.execution_control.errors import CancelRequested, HumanApprovalRequired, PauseRequested
from dare_framework.execution.impl.execution_control.models import ExecutionSignal
from dare_framework.execution.impl.execution_control.protocols import IExecutionControl


@dataclass(frozen=True)
class CheckpointRecord:
    """A minimal persisted checkpoint record (v2.0)."""

    checkpoint_id: str
    created_at: float
    label: str
    payload: dict


class FileExecutionControl(IExecutionControl):
    """Execution control plane with file-based checkpoints (MVP)."""

    def __init__(self, *, event_log: IEventLog, checkpoint_dir: str = ".dare/checkpoints") -> None:
        self._event_log = event_log
        self._checkpoint_dir = Path(checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._signal: ExecutionSignal = ExecutionSignal.NONE

    def poll(self) -> ExecutionSignal:
        return self._signal

    def poll_or_raise(self) -> None:
        signal = self.poll()
        if signal == ExecutionSignal.NONE:
            return
        if signal == ExecutionSignal.PAUSE_REQUESTED:
            raise PauseRequested("pause requested")
        if signal == ExecutionSignal.CANCEL_REQUESTED:
            raise CancelRequested("cancel requested")
        if signal == ExecutionSignal.HUMAN_APPROVAL_REQUIRED:
            raise HumanApprovalRequired("human approval required")

    async def pause(self, reason: str) -> str:
        checkpoint_id = await self.checkpoint("pause", {"reason": reason})
        await self._event_log.append("exec.pause", {"checkpoint_id": checkpoint_id, "reason": reason})
        return checkpoint_id

    async def resume(self, checkpoint_id: str) -> None:
        # Resume is intentionally minimal: it records the action for audit and clears any signal.
        await self._event_log.append("exec.resume", {"checkpoint_id": checkpoint_id})
        self._signal = ExecutionSignal.NONE

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        """Record a HITL waiting point.

        This MVP implementation is intentionally non-blocking: it appends a WORM event and
        returns immediately. A production implementation could block/poll on external
        approval, or surface a resumable waiting state to an external controller/UI.
        """

        await self._event_log.append(
            "exec.waiting_human",
            {"checkpoint_id": checkpoint_id, "reason": reason, "mode": "non_blocking_stub"},
        )

    async def checkpoint(self, label: str, payload: dict) -> str:
        checkpoint_id = uuid4().hex
        record = CheckpointRecord(checkpoint_id=checkpoint_id, created_at=time(), label=label, payload=payload)
        path = self._checkpoint_dir / f"{checkpoint_id}.json"
        path.write_text(json.dumps(asdict(record), sort_keys=True), encoding="utf-8")
        await self._event_log.append("exec.checkpoint", {"checkpoint_id": checkpoint_id, "label": label})
        return checkpoint_id

    # Optional helpers for external systems/tests (not part of IExecutionControl).
    def request_pause(self) -> None:
        self._signal = ExecutionSignal.PAUSE_REQUESTED

    def request_cancel(self) -> None:
        self._signal = ExecutionSignal.CANCEL_REQUESTED

    def request_human_approval(self) -> None:
        self._signal = ExecutionSignal.HUMAN_APPROVAL_REQUIRED
