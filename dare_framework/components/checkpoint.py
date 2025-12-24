from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dare_framework.components.interfaces import ICheckpoint
from dare_framework.core.models import MilestoneSummary, SessionSummary
from dare_framework.core.state import RuntimeState


@dataclass
class InMemoryCheckpoint(ICheckpoint):
    def __init__(self) -> None:
        self._states: dict[str, RuntimeState] = {}
        self._milestone_summaries: dict[str, MilestoneSummary] = {}
        self._session_summaries: dict[str, SessionSummary] = {}
        self._checkpoints: dict[str, RuntimeState] = {}

    async def save(
        self,
        task_id: str,
        state: RuntimeState,
        milestone_id: str | None = None,
    ) -> str:
        checkpoint_id = f"checkpoint_{task_id}_{len(self._checkpoints) + 1}"
        self._states[task_id] = state
        self._checkpoints[checkpoint_id] = state
        return checkpoint_id

    async def load(self, checkpoint_id: str) -> RuntimeState:
        return self._checkpoints.get(checkpoint_id, RuntimeState.READY)

    async def save_milestone_summary(self, milestone_id: str, summary: MilestoneSummary) -> None:
        self._milestone_summaries[milestone_id] = summary

    async def load_milestone_summary(self, milestone_id: str) -> MilestoneSummary:
        summary = self._milestone_summaries.get(milestone_id)
        if summary is None:
            raise KeyError(f"Milestone summary not found: {milestone_id}")
        return summary

    async def is_completed(self, milestone_id: str) -> bool:
        return milestone_id in self._milestone_summaries

    async def save_session_summary(self, summary: SessionSummary) -> None:
        self._session_summaries[summary.session_id] = summary

    async def load_session_summary(self, session_id: str) -> SessionSummary | None:
        return self._session_summaries.get(session_id)
