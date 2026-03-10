"""A2A JSON-RPC method handlers: tasks/send, tasks/get, tasks/cancel."""

from __future__ import annotations

import logging
from typing import Any, Callable
from uuid import uuid4

from dare_framework.a2a.types import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INTERNAL_ERROR,
    JsonRpcRequest,
    JsonRpcResponse,
    jsonrpc_error,
    jsonrpc_result,
    task_state,
)
from dare_framework.a2a.server.message_adapter import (
    message_parts_to_message,
    run_result_to_artifact_dict,
)
from dare_framework.context import Message

logger = logging.getLogger(__name__)


# In-memory task store: task_id -> latest task state dict (for tasks/get and tasks/cancel)
TaskStore = dict[str, dict[str, Any]]


async def handle_tasks_send(
    params: dict[str, Any],
    agent_run: Callable[[Message], Any],
    store: TaskStore,
    workspace_dir: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Handle tasks/send: run agent and return task state with artifacts."""
    task_id = params.get("id")
    if not task_id or not isinstance(task_id, str):
        task_id = str(uuid4())
    message = params.get("message")
    if not message or not isinstance(message, dict):
        raise ValueError("missing or invalid 'message' in params")
    parts = message.get("parts")
    if not isinstance(parts, list):
        parts = []
    session_id = params.get("sessionId") or str(uuid4())
    metadata = dict(params.get("metadata")) if isinstance(params.get("metadata"), dict) else {}
    metadata["task_id"] = task_id
    metadata["a2a_session_id"] = session_id
    input_message = message_parts_to_message(
        parts,
        workspace_dir=workspace_dir,
        metadata=metadata,
    )
    if not input_message.text and not input_message.attachments:
        input_message = Message(
            role=input_message.role,
            kind=input_message.kind,
            text="(No input)",
            attachments=input_message.attachments,
            metadata=dict(input_message.metadata),
        )
    try:
        result = await agent_run(input_message)
    except Exception as e:
        logger.exception("Agent run failed for task %s", task_id)
        state = task_state(
            task_id,
            session_id,
            "failed",
            artifacts=[{"name": "error", "parts": [{"type": "text", "text": str(e)}]}],
            metadata=metadata,
        )
        store[task_id] = state
        return state

    artifact = run_result_to_artifact_dict(
        result,
        artifact_id=f"{task_id}-out",
        name="output",
        task_id=task_id,
        base_url=base_url,
        workspace_dir=workspace_dir,
    )
    state = task_state(
        task_id,
        session_id,
        "completed" if result.success else "failed",
        artifacts=[artifact],
        metadata=metadata,
    )
    store[task_id] = state
    return state


def handle_tasks_get(params: dict[str, Any], store: TaskStore) -> dict[str, Any]:
    """Handle tasks/get: return current task state by id."""
    task_id = params.get("id")
    if not task_id or not isinstance(task_id, str):
        raise ValueError("missing or invalid 'id' in params")
    state = store.get(task_id)
    if state is None:
        raise ValueError(f"task not found: {task_id}")
    return state


def handle_tasks_cancel(params: dict[str, Any], store: TaskStore) -> dict[str, Any]:
    """Handle tasks/cancel: mark task as cancelled (best-effort; DARE may not support cancel yet)."""
    task_id = params.get("id")
    if not task_id or not isinstance(task_id, str):
        raise ValueError("missing or invalid 'id' in params")
    session_id = params.get("sessionId") or ""
    # Update stored state to cancelled if present
    existing = store.get(task_id)
    if existing:
        store[task_id] = {
            **existing,
            "status": {"state": "cancelled"},
            "sessionId": session_id or existing.get("sessionId", ""),
        }
    return task_state(task_id, session_id, "cancelled")


async def dispatch_request(
    request: JsonRpcRequest,
    agent_run: Callable[[Message], Any],
    store: TaskStore,
    workspace_dir: str | None = None,
    base_url: str | None = None,
) -> JsonRpcResponse:
    """Dispatch JSON-RPC method to handler and return response."""
    method = request.get("method")
    params = request.get("params")
    if params is not None and not isinstance(params, dict):
        params = {}
    req_id = request.get("id")

    if method == "tasks/send":
        if params is None:
            return jsonrpc_error(INVALID_PARAMS, "params required", req_id)
        try:
            result = await handle_tasks_send(
                params, agent_run, store, workspace_dir, base_url
            )
            return jsonrpc_result(result, req_id)
        except ValueError as e:
            return jsonrpc_error(INVALID_PARAMS, str(e), req_id)
        except Exception as e:
            logger.exception("tasks/send failed")
            return jsonrpc_error(INTERNAL_ERROR, str(e), req_id)
    if method == "tasks/get":
        if params is None:
            return jsonrpc_error(INVALID_PARAMS, "params required", req_id)
        try:
            result = handle_tasks_get(params, store)
            return jsonrpc_result(result, req_id)
        except ValueError as e:
            return jsonrpc_error(INVALID_PARAMS, str(e), req_id)
    if method == "tasks/cancel":
        if params is None:
            return jsonrpc_error(INVALID_PARAMS, "params required", req_id)
        try:
            result = handle_tasks_cancel(params, store)
            return jsonrpc_result(result, req_id)
        except ValueError as e:
            return jsonrpc_error(INVALID_PARAMS, str(e), req_id)
    return jsonrpc_error(METHOD_NOT_FOUND, f"method not found: {method}", req_id)


async def handle_tasks_send_subscribe_stream(
    params: dict[str, Any],
    agent_run: Callable[[Message], Any],
    store: TaskStore,
    workspace_dir: str | None = None,
    base_url: str | None = None,
):
    """Async generator: yield 'running' event then run task then yield final state event."""
    import json as _json
    task_id = params.get("id") or "unknown"
    session_id = params.get("sessionId") or ""
    # Emit running state first so client knows task started
    running_state = task_state(task_id, session_id, "running")
    yield f"data: {_json.dumps(running_state)}\n\n"
    state = await handle_tasks_send(
        params, agent_run, store, workspace_dir, base_url
    )
    yield f"data: {_json.dumps(state)}\n\n"
