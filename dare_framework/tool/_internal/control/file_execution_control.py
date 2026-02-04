"""File-based execution control implementation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

from dare_framework.tool.exceptions import (
    CancelRequested,
    HumanApprovalRequired,
    PauseRequested,
)
from dare_framework.tool.interfaces import IExecutionControl
from dare_framework.tool.types import ExecutionSignal


@dataclass(frozen=True)
class CheckpointRecord:
    """A minimal persisted checkpoint record."""

    checkpoint_id: str
    created_at: float
    label: str
    payload: dict[str, Any]


class FileExecutionControl(IExecutionControl):
    """Execution control plane with file-based checkpoints."""

    def __init__(
        self,
        *,
        event_log: Any | None = None,
        checkpoint_dir: str = ".dare/checkpoints",
    ) -> None:
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
        if self._event_log is not None:
            await self._event_log.append(
                "exec.pause",
                {"checkpoint_id": checkpoint_id, "reason": reason},
            )
        return checkpoint_id

    async def resume(self, checkpoint_id: str) -> None:
        if self._event_log is not None:
            await self._event_log.append("exec.resume", {"checkpoint_id": checkpoint_id})
        self._signal = ExecutionSignal.NONE

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        if self._event_log is not None:
            await self._event_log.append(
                "exec.waiting_human",
                {
                    "checkpoint_id": checkpoint_id,
                    "reason": reason,
                    "mode": "non_blocking_stub",
                },
            )

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        checkpoint_id = uuid4().hex
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            created_at=time(),
            label=label,
            payload=payload,
        )
        path = self._checkpoint_dir / f"{checkpoint_id}.json"
        path.write_text(json.dumps(asdict(record), sort_keys=True), encoding="utf-8")
        if self._event_log is not None:
            await self._event_log.append(
                "exec.checkpoint",
                {"checkpoint_id": checkpoint_id, "label": label},
            )
        return checkpoint_id

    def request_pause(self) -> None:
        self._signal = ExecutionSignal.PAUSE_REQUESTED

    def request_cancel(self) -> None:
        self._signal = ExecutionSignal.CANCEL_REQUESTED

    def request_human_approval(self) -> None:
        self._signal = ExecutionSignal.HUMAN_APPROVAL_REQUIRED
