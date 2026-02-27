"""Human-readable stdout renderer."""

from __future__ import annotations

from typing import Any

from client.session import ExecutionMode


class HumanRenderer:
    """Console renderer for interactive and one-shot modes."""

    def __init__(self, *, width: int = 72) -> None:
        self._width = width

    def header(self, title: str) -> None:
        rule = "=" * self._width
        print(f"\n{rule}\n{title}\n{rule}\n", flush=True)

    def message(self, text: str) -> None:
        print(text, flush=True)

    def info(self, text: str) -> None:
        print(f"[INFO] {text}", flush=True)

    def warn(self, text: str) -> None:
        print(f"[WARN] {text}", flush=True)

    def ok(self, text: str) -> None:
        print(f"[OK] {text}", flush=True)

    def error(self, text: str) -> None:
        print(f"[ERR] {text}", flush=True)

    def show_mode(self, mode: ExecutionMode) -> None:
        self.info(f"mode={mode.value}")

    def show_plan(self, plan: Any) -> None:
        self.header("PLAN PREVIEW")
        print(f"Goal: {plan.plan_description}\n", flush=True)
        if not getattr(plan, "steps", None):
            print("(no steps)", flush=True)
            return
        for index, step in enumerate(plan.steps, 1):
            title = step.description or step.capability_id
            print(f"{index}. {title}", flush=True)
            print(f"   evidence: {step.capability_id}", flush=True)
            params = getattr(step, "params", None)
            if params:
                print(f"   params: {params}", flush=True)
        print(flush=True)

    def show_json(self, payload: Any) -> None:
        print(payload, flush=True)
