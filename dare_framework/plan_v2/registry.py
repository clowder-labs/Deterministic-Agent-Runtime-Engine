"""Sub-agent registry: id + capability_description + factory. Used by Plan Agent to expose sub-agents as tools."""

from __future__ import annotations

from typing import Any, Callable, Protocol


class IRunnable(Protocol):
    """Protocol for sub-agent: must have run(message) returning awaitable with .output or str."""

    async def run(self, message: str, **kwargs: Any) -> Any:
        ...


# Factory: no args, returns an IRunnable (e.g. ReactAgent). Called on each tool invocation.
SubAgentFactory = Callable[[], Any]


class SubAgentRegistry:
    """Registry of sub-agents by id. Each entry has capability_description (for tool description) and factory (instantiate on call)."""

    def __init__(self) -> None:
        # id -> (capability_description, factory)
        self._entries: dict[str, tuple[str, SubAgentFactory]] = {}

    def register(
        self,
        sub_agent_id: str,
        capability_description: str,
        factory: SubAgentFactory,
    ) -> None:
        """Register a sub-agent. capability_description is shown to the Plan Agent for function call selection."""
        if not sub_agent_id or not capability_description.strip():
            raise ValueError("sub_agent_id and capability_description must be non-empty")
        self._entries[sub_agent_id] = (capability_description.strip(), factory)

    def get_description(self, sub_agent_id: str) -> str:
        """Return capability_description for the given id."""
        entry = self._entries.get(sub_agent_id)
        if entry is None:
            raise KeyError(f"Sub-agent not registered: {sub_agent_id}")
        return entry[0]

    def ids(self) -> list[str]:
        """Return all registered sub-agent ids."""
        return list(self._entries.keys())

    def __contains__(self, sub_agent_id: str) -> bool:
        return sub_agent_id in self._entries

    async def run(self, sub_agent_id: str, task: str, **kwargs: Any) -> Any:
        """Instantiate the sub-agent and run with the given task. Returns result (e.g. RunResult.output or str)."""
        entry = self._entries.get(sub_agent_id)
        if entry is None:
            raise KeyError(f"Sub-agent not registered: {sub_agent_id}")
        _, factory = entry
        agent = factory()
        result = await agent.run(task, **kwargs)
        if hasattr(result, "output"):
            return result.output
        if hasattr(result, "output_text") and result.output_text:
            return result.output_text
        return result


__all__ = ["IRunnable", "SubAgentFactory", "SubAgentRegistry"]
