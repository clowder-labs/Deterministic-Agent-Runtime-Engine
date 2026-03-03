"""Planner: holds PlannerState and exposes plan tools as IToolProvider. Mount on ReactAgent as Plan Agent."""

from __future__ import annotations

from dare_framework.tool.kernel import ITool, IToolProvider

from dare_framework.plan_v2.registry import SubAgentRegistry
from dare_framework.plan_v2.types import PlannerState
from dare_framework.plan_v2.tools import (
    CreatePlanTool,
    DecomposeTaskTool,
    FinishPlanTool,
    ReflectTool,
    ReviseCurrentPlanTool,
    SubAgentTool,
    ValidatePlanTool,
    VerifyMilestoneTool,
)


class Planner(IToolProvider):
    """Plan state + plan tools. Optionally register sub-agents so Plan Agent can delegate steps via tools."""

    def __init__(
        self,
        state: PlannerState | None = None,
        sub_agent_registry: SubAgentRegistry | None = None,
        *,
        plan_tools: bool = True,
    ) -> None:
        """plan_tools=False: 仅提供 sub_agent 工具，不提供 create_plan/validate_plan 等（意图驱动模式）。"""
        self._state = state if state is not None else PlannerState()
        self._registry = sub_agent_registry

        self._tools: list[ITool] = []
        if plan_tools:
            self._tools.extend(
                [
                    CreatePlanTool(self._state),
                    ValidatePlanTool(self._state),
                    ReviseCurrentPlanTool(self._state),
                    FinishPlanTool(self._state),
                    VerifyMilestoneTool(self._state),
                    ReflectTool(self._state),
                    DecomposeTaskTool(self._state),
                ]
            )
        if self._registry is not None:
            for sub_id in self._registry.ids():
                self._tools.append(SubAgentTool(self._registry, sub_id, self._state))

    @property
    def state(self) -> PlannerState:
        """PlannerState for this planner. Orchestrator can read it and call copy_for_execution() for Execution Agent."""
        return self._state

    def list_tools(self) -> list[ITool]:
        return list(self._tools)


__all__ = ["Planner"]
