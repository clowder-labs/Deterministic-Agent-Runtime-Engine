"""Local JSONL capture hook for per-call LLM input/output observation.

Records are appended to a file keyed by conversation (if available) or run id.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dare_framework.config.types import Config
from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY_VALUES


def _safe_run_id(raw: str) -> str:
    normalized = raw.strip()
    if not normalized:
        return "unknown"
    chars: list[str] = []
    for ch in normalized:
        if ch.isalnum() or ch in {"-", "_"}:
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class LLMIOCaptureHook(IHook):
    """Capture each model request/response pair into local JSONL files."""

    def __init__(self, *, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._pending_requests: dict[tuple[str, int], dict[str, Any]] = {}
        self._fallback_iteration = 0

    @property
    def name(self) -> str:
        return "llm_io_capture"

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = args
        payload = kwargs.get("payload")
        if not isinstance(payload, dict):
            return HookResult(decision=HookDecision.ALLOW)

        try:
            if phase is HookPhase.BEFORE_MODEL:
                self._on_before_model(payload)
            elif phase is HookPhase.AFTER_MODEL:
                self._on_after_model(payload)
        except Exception:
            # Observability hooks are best-effort and must never block runtime flow.
            return HookResult(decision=HookDecision.ALLOW)
        return HookResult(decision=HookDecision.ALLOW)

    def _on_before_model(self, payload: dict[str, Any]) -> None:
        model_input = payload.get("model_input")
        if not isinstance(model_input, ModelInput):
            return

        run_id = self._extract_run_id(payload)
        conversation_id = self._extract_conversation_id(payload)
        iteration = self._extract_iteration(payload, run_id=run_id, create_if_missing=True)
        key = (run_id, iteration)
        self._pending_requests[key] = {
            "run_id": run_id,
            "conversation_id": conversation_id,
            "task_id": payload.get("task_id"),
            "context_id": payload.get("context_id"),
            "iteration": iteration,
            "model_name": payload.get("model_name"),
            "request": {
                "messages": [
                    {
                        "id": message.id,
                        "role": str(message.role),
                        "kind": str(getattr(message, "kind", "")),
                        "name": message.name,
                        "text": getattr(message, "text", None),
                        "attachments": [
                            {
                                "kind": str(attachment.kind),
                                "uri": attachment.uri,
                                "mime_type": attachment.mime_type,
                                "filename": attachment.filename,
                                "metadata": dict(attachment.metadata),
                            }
                            for attachment in getattr(message, "attachments", [])
                        ],
                        "data": dict(message.data) if isinstance(getattr(message, "data", None), dict) else None,
                        "metadata": dict(message.metadata),
                    }
                    for message in model_input.messages
                ],
                "tools": [
                    {
                        "id": tool.id,
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in model_input.tools
                ],
                "metadata": dict(model_input.metadata),
            },
        }

    def _on_after_model(self, payload: dict[str, Any]) -> None:
        run_id = self._extract_run_id(payload)
        payload_conversation_id = self._extract_conversation_id(payload)
        iteration = self._extract_iteration(payload, run_id=run_id, create_if_missing=False)
        key = (run_id, iteration)

        request_snapshot = self._pending_requests.pop(key, None)
        if request_snapshot is None:
            request_snapshot = {
                "run_id": run_id,
                "conversation_id": payload_conversation_id,
                "task_id": payload.get("task_id"),
                "context_id": payload.get("context_id"),
                "iteration": iteration,
                "model_name": payload.get("model_name"),
                "request": {
                    "messages": [],
                    "tools": [],
                    "metadata": {},
                },
            }

        model_output = payload.get("model_output")
        if not isinstance(model_output, dict):
            model_output = {}

        usage = payload.get("model_usage")
        if not isinstance(usage, dict):
            usage = {}

        conversation_id = request_snapshot.get("conversation_id") or payload_conversation_id
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": request_snapshot.get("run_id"),
            "conversation_id": conversation_id,
            "task_id": request_snapshot.get("task_id"),
            "context_id": request_snapshot.get("context_id"),
            "iteration": request_snapshot.get("iteration"),
            "model_name": request_snapshot.get("model_name"),
            "request": request_snapshot.get("request"),
            "response": {
                "content": model_output.get("content", ""),
                "tool_calls": model_output.get("tool_calls", []),
                "metadata": model_output.get("metadata", {}),
            },
            "usage": usage,
            "duration_ms": _to_float(payload.get("duration_ms"), 0.0),
        }

        trace_key = conversation_id if isinstance(conversation_id, str) and conversation_id else run_id
        self._append_record(trace_key, record)

    def _extract_run_id(self, payload: dict[str, Any]) -> str:
        raw = payload.get("run_id")
        if isinstance(raw, str) and raw.strip():
            return _safe_run_id(raw)
        return "unknown"

    def _extract_conversation_id(self, payload: dict[str, Any]) -> str | None:
        raw = payload.get("conversation_id")
        if isinstance(raw, str) and raw.strip():
            return _safe_run_id(raw)
        return None

    def _extract_iteration(self, payload: dict[str, Any], *, run_id: str, create_if_missing: bool) -> int:
        raw_iteration = payload.get("iteration")
        if isinstance(raw_iteration, int) and raw_iteration > 0:
            return raw_iteration
        if create_if_missing:
            self._fallback_iteration += 1
            return self._fallback_iteration

        candidates = [idx for current_run_id, idx in self._pending_requests if current_run_id == run_id]
        if candidates:
            return max(candidates)
        return _to_int(raw_iteration, default=0)

    def _trace_path_for_run(self, run_id: str) -> Path:
        return self._base_dir / f"{_safe_run_id(run_id)}.llm_io.jsonl"

    def _append_record(self, run_id: str, record: dict[str, Any]) -> None:
        trace_path = self._trace_path_for_run(run_id)
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str))
            f.write("\n")


def create_default_llm_io_capture_hook(config: Config) -> LLMIOCaptureHook | None:
    """Create a default local capture hook from config/env toggles."""
    if config is None:
        return None

    enabled_by_config = bool(config.observability.capture_content)
    enabled_by_env = _is_truthy(os.getenv("DARE_LLM_IO_CAPTURE"))
    if not enabled_by_config and not enabled_by_env:
        return None

    custom_dir = os.getenv("DARE_LLM_IO_DIR")
    if custom_dir:
        base_dir = Path(custom_dir).expanduser()
    else:
        base_dir = Path(config.workspace_dir) / ".dare" / "observability" / "llm_io"
    return LLMIOCaptureHook(base_dir=base_dir)


def summarize_llm_io_trace(trace_path: str | Path) -> dict[str, Any]:
    """Summarize model-call usage from a captured JSONL trace file."""
    path = Path(trace_path)
    summary = {
        "trace_path": str(path),
        "model_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "duration_ms": 0.0,
    }
    if not path.exists():
        return summary

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        summary["model_calls"] += 1
        usage = record.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        prompt_tokens = _to_int(usage.get("prompt_tokens", usage.get("input_tokens", 0)))
        completion_tokens = _to_int(usage.get("completion_tokens", usage.get("output_tokens", 0)))
        total_tokens = _to_int(usage.get("total_tokens", prompt_tokens + completion_tokens))
        summary["prompt_tokens"] += prompt_tokens
        summary["completion_tokens"] += completion_tokens
        summary["total_tokens"] += total_tokens
        summary["duration_ms"] += _to_float(record.get("duration_ms"), 0.0)

    return summary


__all__ = [
    "LLMIOCaptureHook",
    "create_default_llm_io_capture_hook",
    "summarize_llm_io_trace",
]
