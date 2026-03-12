"""Supported default checkpoint implementations and contributors.

This module keeps legacy checkpoint symbols importable after checkpoint internals
were consolidated into ``dare_framework.checkpoint.kernel``.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any
from uuid import uuid4

from dare_framework.context.types import Message

STM = "stm"
SESSION_STATE = "session_state"
SESSION_CONTEXT = "session_context"
WORKSPACE_FILES = "workspace_files"


class MemoryCheckpointStore:
    """In-memory checkpoint payload store kept for facade compatibility."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def put(self, checkpoint_id: str, payload: dict[str, Any]) -> None:
        self._store[checkpoint_id] = _clone_payload(payload)

    def get(self, checkpoint_id: str) -> dict[str, Any] | None:
        if checkpoint_id not in self._store:
            return None
        return _clone_payload(self._store[checkpoint_id])

    def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._store:
            del self._store[checkpoint_id]
            return True
        return False


def _scope_keys(scope: Any, method_name: str) -> list[str]:
    method = getattr(scope, method_name, None)
    if callable(method):
        values = method()
        if isinstance(values, (list, tuple, set)):
            return [str(v) for v in values]
    if isinstance(scope, (list, tuple, set)):
        return [str(v) for v in scope]
    return []


def _clone_payload(value: Any) -> Any:
    """Clone nested checkpoint payloads so save/restore stays side-effect free."""
    return deepcopy(value)


class DefaultCheckpointSaveRestore:
    """Legacy save/restore coordinator over contributor payload components."""

    def __init__(self, store: MemoryCheckpointStore, contributors: list[Any]) -> None:
        self._store = store
        self._contributors = {
            str(c.component_key): c
            for c in contributors
            if getattr(c, "component_key", None) is not None
        }

    def save(self, scope: Any, ctx: Any) -> str:
        payload: dict[str, Any] = {}
        for key in _scope_keys(scope, "keys_for_save"):
            contributor = self._contributors.get(key)
            if contributor is None:
                continue
            payload[key] = contributor.serialize(ctx)
        checkpoint_id = uuid4().hex[:16]
        self._store.put(checkpoint_id, payload)
        return checkpoint_id

    def restore(self, checkpoint_id: str, scope: Any, ctx: Any) -> None:
        payload = self._store.get(checkpoint_id)
        if payload is None:
            raise LookupError(f"Checkpoint not found: {checkpoint_id!r}")
        for key in _scope_keys(scope, "keys_for_restore"):
            if key not in payload:
                continue
            contributor = self._contributors.get(key)
            if contributor is None:
                continue
            contributor.deserialize_and_apply(payload[key], ctx)


class StmContributor:
    """Serialize/restore short-term memory messages."""

    component_key = STM

    def serialize(self, ctx: Any) -> list[dict[str, Any]]:
        context = getattr(ctx, "context", None)
        if context is None:
            return []
        messages = context.stm_get()
        return [
            {
                "role": m.role,
                "kind": m.kind,
                "text": m.text,
                "attachments": [
                    {
                        "kind": attachment.kind,
                        "uri": attachment.uri,
                        "mime_type": attachment.mime_type,
                        "filename": attachment.filename,
                        "metadata": _clone_payload(getattr(attachment, "metadata", {}) or {}),
                    }
                    for attachment in m.attachments
                ],
                "data": _clone_payload(m.data),
                "name": m.name,
                "metadata": _clone_payload(getattr(m, "metadata", {}) or {}),
                "mark": getattr(m, "mark", None),
                "id": getattr(m, "id", None),
            }
            for m in messages
        ]

    def deserialize_and_apply(self, payload: list[Any], ctx: Any) -> None:
        context = getattr(ctx, "context", None)
        if context is None:
            return
        context.stm_clear()
        for item in payload or []:
            if not isinstance(item, dict):
                continue
            restored_text = item["text"] if "text" in item else item.get("content", "")
            context.stm_add(
                Message(
                    role=item.get("role", "user"),
                    kind=item.get("kind", "chat"),
                    text=restored_text,
                    attachments=_clone_payload(item.get("attachments")) or [],
                    data=_clone_payload(item.get("data")),
                    name=item.get("name"),
                    metadata=dict(item.get("metadata") or {}),
                    mark=item.get("mark", "temporary"),
                    id=item.get("id"),
                )
            )


class SessionStateContributor:
    """Serialize/restore minimal session-state fields."""

    component_key = SESSION_STATE

    def serialize(self, ctx: Any) -> dict[str, Any] | None:
        state = getattr(ctx, "session_state", None)
        if state is None:
            return None
        try:
            return asdict(state)
        except Exception:
            return {
                "current_milestone_idx": getattr(state, "current_milestone_idx", None),
                "task_id": getattr(state, "task_id", None),
                "run_id": getattr(state, "run_id", None),
            }

    def deserialize_and_apply(self, payload: Any, ctx: Any) -> None:
        state = getattr(ctx, "session_state", None)
        if state is None or not isinstance(payload, dict):
            return
        if "current_milestone_idx" in payload and hasattr(state, "current_milestone_idx"):
            state.current_milestone_idx = payload["current_milestone_idx"]
        if "task_id" in payload and hasattr(state, "task_id"):
            state.task_id = payload["task_id"]
        if "run_id" in payload and hasattr(state, "run_id"):
            state.run_id = payload["run_id"]


class SessionContextContributor:
    """Serialize session context for audit trails (restore intentionally no-op)."""

    component_key = SESSION_CONTEXT

    def serialize(self, ctx: Any) -> dict[str, Any] | None:
        session_context = getattr(ctx, "session_context", None)
        if session_context is None:
            return None
        try:
            serialized = asdict(session_context)
        except Exception:
            return {
                "session_id": getattr(session_context, "session_id", None),
                "task_id": getattr(session_context, "task_id", None),
            }
        config_value = serialized.get("config")
        if config_value is not None and not isinstance(config_value, dict):
            try:
                serialized["config"] = asdict(config_value)
            except Exception:
                serialized["config"] = None
        return serialized

    def deserialize_and_apply(self, payload: Any, ctx: Any) -> None:
        _ = (payload, ctx)
        # SessionContext is construction-time state; legacy restore path keeps this as no-op.


class WorkspaceGitContributor:
    """Compatibility no-op contributor after workspace-git checkpoint removal."""

    component_key = WORKSPACE_FILES

    def serialize(self, ctx: Any) -> dict[str, Any]:
        _ = ctx
        return {}

    def deserialize_and_apply(self, payload: Any, ctx: Any) -> None:
        _ = (payload, ctx)

__all__ = [
    "MemoryCheckpointStore",
    "DefaultCheckpointSaveRestore",
    "StmContributor",
    "WorkspaceGitContributor",
    "SessionStateContributor",
    "SessionContextContributor",
]
