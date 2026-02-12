"""Agent domain lifecycle status enum."""

from __future__ import annotations

from enum import StrEnum


class AgentStatus(StrEnum):
    """Canonical runtime lifecycle states for an agent instance."""

    INIT = "init"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


__all__ = ["AgentStatus"]
