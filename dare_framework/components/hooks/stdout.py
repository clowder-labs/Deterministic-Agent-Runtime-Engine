from __future__ import annotations

import sys
from typing import Any

from dare_framework.components.hooks.protocols import IHook
from dare_framework.contracts import ComponentType
from dare_framework.core.hook.models import HookPhase


class StdoutHook(IHook):
    """Hook that prints human-readable summaries of Kernel events to stdout."""

    component_type = ComponentType.HOOK

    @property
    def phase(self) -> HookPhase:
        return HookPhase.ON_EVENT

    def __call__(self, payload: dict[str, Any]) -> Any:
        event_type = payload.get("event_type")
        event_payload = payload.get("payload", {})

        if event_type == "plan.validated":
            print(f"[DARE:PLAN] {event_payload.get('plan_description')}")
        elif event_type == "model.response":
            content = event_payload.get("content", "")
            if content:
                print(f"[DARE:MODEL] {content}")
            for tc in event_payload.get("tool_calls", []):
                name = tc.get("name")
                args = tc.get("arguments")
                print(f"[DARE:TOOL_CALL] {name}({args})")
        elif event_type == "tool.result":
            success = "SUCCESS" if event_payload.get("success") else "FAILED"
            cap_id = event_payload.get("capability_id")
            print(f"[DARE:TOOL_RESULT] {cap_id} -> {success}")
        elif event_type == "session.start":
            print(f"[DARE:SESSION] Starting task: {event_payload.get('task_id')}")

        sys.stdout.flush()
