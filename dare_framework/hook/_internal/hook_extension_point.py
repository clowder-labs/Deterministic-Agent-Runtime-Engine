"""Default extension point implementation that dispatches to hooks."""

from __future__ import annotations

import logging
from typing import Any

from dare_framework.hook._internal.decision_arbiter import arbitrate
from dare_framework.hook._internal.hook_runner import run_with_policy
from dare_framework.hook._internal.hook_selector import sort_hook_specs
from dare_framework.hook._internal.patch_validator import merge_patches
from dare_framework.hook.kernel import HookFn, IExtensionPoint, IHook
from dare_framework.hook.types import HookDecision, HookPhase, HookResult

_logger = logging.getLogger("dare.hook")

_PATCH_ALLOWLIST_BY_PHASE: dict[HookPhase, tuple[str, ...]] = {
    HookPhase.BEFORE_MODEL: ("model_input",),
    HookPhase.BEFORE_CONTEXT_ASSEMBLE: ("context_patch",),
}


class HookExtensionPoint(IExtensionPoint):
    """Dispatch hook payloads to registered hook functions and components."""

    def __init__(
        self,
        hooks: list[IHook] | None = None,
        *,
        timeout_ms: int = 200,
        retries: int = 0,
        idempotent: bool = False,
        enforce: bool = True,
    ) -> None:
        self._hooks = list(hooks) if hooks is not None else []
        self._callbacks: dict[HookPhase, list[HookFn]] = {}
        self._callback_specs: dict[HookPhase, list[dict[str, Any]]] = {}
        self._registration_order = 0
        self._timeout_ms = timeout_ms
        self._retries = retries
        self._idempotent = idempotent
        self._enforce = enforce

    def register_hook(self, phase: HookPhase, hook: HookFn) -> None:
        self._callbacks.setdefault(phase, []).append(hook)
        self._registration_order += 1
        self._callback_specs.setdefault(phase, []).append(
            {
                "phase": phase.value,
                "lane": "observe",
                "priority": 100,
                "source": "code",
                "registration_order": self._registration_order,
                "callback": hook,
            }
        )

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        decisions: list[dict[str, Any]] = []
        errors: list[str] = []

        callback_specs = sort_hook_specs(list(self._callback_specs.get(phase, [])))
        callbacks = [spec["callback"] for spec in callback_specs]
        if not callbacks:
            callbacks = list(self._callbacks.get(phase, []))
        for callback in callbacks:
            run_result = await run_with_policy(
                lambda cb=callback: cb(payload),
                timeout_ms=self._timeout_ms,
                retries=self._retries,
                idempotent=self._idempotent,
            )
            decisions.append(self._normalize_runner_result(run_result))
            if run_result.error_code:
                errors.append(f"{run_result.error_code}:{run_result.message or ''}")

        for hook in self._hooks:
            run_result = await run_with_policy(
                lambda h=hook: h.invoke(phase, payload=payload),
                timeout_ms=self._timeout_ms,
                retries=self._retries,
                idempotent=self._idempotent,
            )
            decisions.append(self._normalize_runner_result(run_result))
            if run_result.error_code:
                errors.append(f"{run_result.error_code}:{run_result.message or ''}")

        winner = arbitrate(decisions)
        patch_result = merge_patches(
            [item.get("patch") for item in decisions if item.get("patch") is not None],
            allowlist=_PATCH_ALLOWLIST_BY_PHASE.get(phase, tuple()),
        )
        if patch_result.error_code:
            errors.append(f"{patch_result.error_code}:{patch_result.message or ''}")
            if not self._enforce:
                return HookResult(
                    decision=HookDecision.ALLOW,
                    message=f"shadow mode: {'; '.join(errors)}",
                )
            return HookResult(decision=HookDecision.BLOCK, message="; ".join(errors))

        try:
            decision = HookDecision(str(winner.get("decision", "allow")).lower())
        except ValueError:
            decision = HookDecision.ALLOW

        message = "; ".join(errors) if errors else winner.get("message")
        if not self._enforce and decision is not HookDecision.ALLOW:
            shadow_message = f"shadow mode observed decision={decision.value}"
            if message:
                shadow_message = f"{shadow_message}; {message}"
            return HookResult(
                decision=HookDecision.ALLOW,
                patch=patch_result.patch,
                message=shadow_message,
            )
        return HookResult(decision=decision, patch=patch_result.patch, message=message)

    def _normalize_runner_result(self, run_result: Any) -> dict[str, Any]:
        if run_result.error_code:
            _logger.warning("Hook execution degraded to allow: %s", run_result.error_code)
            return {"decision": HookDecision.ALLOW.value, "message": run_result.error_code}
        value = run_result.value
        if isinstance(value, HookResult):
            return {
                "decision": value.decision.value,
                "patch": value.patch,
                "message": value.message,
            }
        if isinstance(value, dict):
            normalized = dict(value)
            normalized["decision"] = str(normalized.get("decision", HookDecision.ALLOW.value)).lower()
            return normalized
        return {"decision": HookDecision.ALLOW.value}


__all__ = ["HookExtensionPoint"]
