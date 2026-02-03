"""Session summary persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dare_framework.agent.types import ISessionSummaryStore
from dare_framework.plan.types import SessionSummary


@dataclass
class FileSessionSummaryStore(ISessionSummaryStore):
    """Persist session summaries to JSON files.

    If base_dir is not provided, uses `.dare/<agent_name>/session_summaries`.
    """

    agent_name: str | None = None
    base_dir: str | Path | None = None

    def __post_init__(self) -> None:
        if self.base_dir is None:
            if not self.agent_name:
                raise ValueError("agent_name is required when base_dir is not provided")
            self._base_dir = Path(".dare") / self.agent_name / "session_summaries"
        else:
            self._base_dir = Path(self.base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, summary: SessionSummary) -> None:
        path = self._base_dir / f"{summary.session_id}.json"
        payload = json.dumps(
            summary.to_dict(),
            sort_keys=True,
            ensure_ascii=True,
            indent=2,
            default=str,
        )
        path.write_text(payload, encoding="utf-8")


__all__ = ["FileSessionSummaryStore"]
