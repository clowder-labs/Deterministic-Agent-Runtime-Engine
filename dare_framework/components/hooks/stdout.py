from __future__ import annotations

import json
from typing import Any

from ...core.runtime import IHook
from ...core.models.config import ComponentType
from ...core.models.event import Event
from ..base_component import ConfigurableComponent


class StdoutHook(ConfigurableComponent, IHook):
    component_type = ComponentType.HOOK
    name = "stdout"

    async def on_event(self, event: Event) -> None:
        event_type = event.event_type
        payload = event.payload

        if event_type == "runtime.run":
            self._print(f"[runtime] run_id={payload.get('run_id')} task_id={payload.get('task_id')}")
            return
        if event_type == "runtime.complete":
            self._print(f"[runtime.complete] success={payload.get('success')}")
            return
        if event_type == "plan.attempt":
            self._print(
                f"[plan] attempt={payload.get('attempt')} desc={payload.get('plan_description','')}"
            )
            self._print_steps(payload.get("steps", []))
            return
        if event_type == "plan.validated":
            self._print(f"[plan.validated] desc={payload.get('plan_description','')}")
            self._print_steps(payload.get("steps", []))
            return
        if event_type == "plan.invalid":
            errors = payload.get("errors", [])
            self._print(
                f"[plan.invalid] desc={payload.get('plan_description','')} errors={self._format(errors)}"
            )
            return
        if event_type == "model.response":
            self._print(f"[model] content={payload.get('content','')}")
            tool_calls = payload.get("tool_calls", [])
            if tool_calls:
                self._print(f"[model.tools] {self._format(tool_calls)}")
            return
        if event_type == "tool.invoke":
            self._print(
                f"[tool.invoke] name={payload.get('tool')} args={self._format(payload.get('args'))}"
            )
            return
        if event_type == "tool.result":
            self._print(
                "[tool.result] name={name} success={success} output={output} error={error}".format(
                    name=payload.get("tool"),
                    success=payload.get("success"),
                    output=self._format(payload.get("output")),
                    error=payload.get("error"),
                )
            )
            return
        if event_type == "tool.error":
            self._print(f"[tool.error] name={payload.get('tool')} error={payload.get('error')}")
            return

    def _print_steps(self, steps: list[dict[str, Any]]) -> None:
        for step in steps:
            self._print(
                "[plan.step] tool={tool} desc={desc} input={tool_input}".format(
                    tool=step.get("tool_name"),
                    desc=step.get("description", ""),
                    tool_input=self._format(step.get("tool_input")),
                )
            )

    def _print(self, line: str) -> None:
        print(line, flush=True)

    def _format(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=True)
        return "" if value is None else str(value)
