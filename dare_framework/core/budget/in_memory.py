from __future__ import annotations

import time
from dataclasses import dataclass, field

from dare_framework.core.budget import Budget, IResourceManager, ResourceExhausted, ResourceType


@dataclass
class _ScopeState:
    start_time: float = field(default_factory=time.time)
    tool_calls: float = 0.0
    tokens: float = 0.0
    cost: float = 0.0


class InMemoryResourceManager(IResourceManager):
    """A simple, coarse-grained resource manager suitable for MVP and tests."""

    def __init__(self, *, default_budget: Budget | None = None, budgets: dict[str, Budget] | None = None) -> None:
        self._default_budget = default_budget or Budget()
        self._budgets = dict(budgets) if budgets else {}
        self._states: dict[str, _ScopeState] = {}

    def get_budget(self, scope: str) -> Budget:
        return self._budgets.get(scope, self._default_budget)

    def acquire(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        # The MVP uses a single accounting path; acquire() exists for future reservation semantics.
        self.record(resource, amount, scope=scope)
        self.check_limit(scope=scope)

    def record(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        state = self._states.setdefault(scope, _ScopeState())
        if resource == ResourceType.TOOL_CALLS:
            state.tool_calls += amount
            return
        if resource == ResourceType.TIME_SECONDS:
            # Time is derived from wall clock; no direct recording needed for MVP.
            return
        if resource == ResourceType.TOKENS:
            state.tokens += amount
            return
        if resource == ResourceType.COST:
            state.cost += amount
            return

    def check_limit(self, *, scope: str) -> None:
        budget = self.get_budget(scope)
        state = self._states.setdefault(scope, _ScopeState())

        if budget.max_tool_calls is not None and state.tool_calls > budget.max_tool_calls:
            raise ResourceExhausted(
                f"Tool call budget exceeded for scope '{scope}': {state.tool_calls} > {budget.max_tool_calls}"
            )

        if budget.max_time_seconds is not None:
            elapsed = time.time() - state.start_time
            if elapsed > budget.max_time_seconds:
                raise ResourceExhausted(
                    f"Time budget exceeded for scope '{scope}': {elapsed:.2f}s > {budget.max_time_seconds}s"
                )

        if budget.max_tokens is not None and state.tokens > budget.max_tokens:
            raise ResourceExhausted(
                f"Token budget exceeded for scope '{scope}': {state.tokens} > {budget.max_tokens}"
            )

        if budget.max_cost is not None and state.cost > budget.max_cost:
            raise ResourceExhausted(f"Cost budget exceeded for scope '{scope}': {state.cost} > {budget.max_cost}")
