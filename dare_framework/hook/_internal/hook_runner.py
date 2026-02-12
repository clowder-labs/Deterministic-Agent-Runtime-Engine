"""Policy runner for governed hook invocation."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class HookRunResult:
    """Normalized execution result for hook invocation policies."""

    value: Any | None = None
    error_code: str | None = None
    message: str | None = None
    attempts: int = 0


async def _call(fn: Callable[[], Any] | Callable[[], Awaitable[Any]]) -> Any:
    outcome = fn()
    if inspect.isawaitable(outcome):
        return await outcome
    return outcome


async def run_with_policy(
    fn: Callable[[], Any] | Callable[[], Awaitable[Any]],
    *,
    timeout_ms: int,
    retries: int,
    idempotent: bool,
) -> HookRunResult:
    """Run hook function with timeout and retry behavior."""

    max_attempts = 1 + (retries if idempotent else 0)
    timeout_seconds = max(float(timeout_ms), 0.0) / 1000.0
    for attempt in range(1, max_attempts + 1):
        try:
            value = await asyncio.wait_for(_call(fn), timeout=timeout_seconds)
            return HookRunResult(value=value, attempts=attempt)
        except asyncio.TimeoutError:
            return HookRunResult(
                error_code="HOOK_TIMEOUT",
                message="hook execution timed out",
                attempts=attempt,
            )
        except Exception as exc:
            if attempt >= max_attempts:
                return HookRunResult(
                    error_code="HOOK_RUNTIME_ERROR",
                    message=str(exc),
                    attempts=attempt,
                )
    return HookRunResult(error_code="HOOK_RUNTIME_ERROR", message="unknown hook runner state", attempts=max_attempts)


__all__ = ["HookRunResult", "run_with_policy"]
