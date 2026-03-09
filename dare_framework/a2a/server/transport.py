"""A2A HTTP transport: ASGI app with /.well-known/agent.json and JSON-RPC POST (a2acn.com)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from dare_framework.a2a.types import (
    INVALID_REQUEST,
    PARSE_ERROR,
    JsonRpcRequest,
    jsonrpc_error,
)
from dare_framework.a2a.server.handlers import (
    TaskStore,
    dispatch_request,
    handle_tasks_send_subscribe_stream,
)

logger = logging.getLogger(__name__)


def create_a2a_app(
    agent_card_json: dict[str, Any],
    agent_run: Callable[[Any], Any],
    store: TaskStore | None = None,
    workspace_dir: str | None = None,
    auth_validate: Callable[[str], bool] | None = None,
) -> Any:
    """Create an ASGI app for A2A: GET /.well-known/agent.json and POST / for JSON-RPC.

    Args:
        agent_card_json: AgentCard dict to serve at /.well-known/agent.json.
        agent_run: Async callable(message: canonical Message) -> RunResult (e.g. agent.run).
        store: Optional shared task store; one is created if not provided.
        workspace_dir: Optional workspace path for resolving FilePart attachments (inline/URI -> temp files).
        auth_validate: Optional callable(token: str) -> bool. If set, POST / and GET /a2a/artifacts/ require
            Authorization: Bearer <token> and reject with 401 when validation returns False.

    Returns:
        Starlette Application instance.
    """
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response, StreamingResponse
        from starlette.routing import Route
    except ImportError as e:
        raise ImportError(
            "starlette is required for A2A server. Install with: pip install starlette"
        ) from e

    task_store: TaskStore = store if store is not None else {}
    base_url = (agent_card_json.get("url") or "").rstrip("/") if isinstance(agent_card_json, dict) else ""

    async def well_known_agent(_request: Request) -> Response:
        return JSONResponse(agent_card_json)

    def _check_auth(request: Request) -> Response | None:
        """Return 401 Response if auth_validate is set and request is unauthorized; else None."""
        if auth_validate is None:
            return None
        auth_h = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_h or not auth_h.startswith("Bearer "):
            return JSONResponse({"error": "Unauthorized", "message": "Bearer token required"}, status_code=401)
        token = auth_h[7:].strip()
        if not auth_validate(token):
            return JSONResponse({"error": "Unauthorized", "message": "Invalid token"}, status_code=401)
        return None

    async def serve_artifact(request: Request) -> Response:
        """Serve artifact file for URI-based FilePart (GET /a2a/artifacts/{task_id}/{filename})."""
        from pathlib import Path
        from starlette.responses import FileResponse, PlainTextResponse
        unauth = _check_auth(request)
        if unauth is not None:
            return unauth
        task_id = request.path_params.get("task_id")
        filename = request.path_params.get("filename")
        if not task_id or not filename or ".." in task_id or ".." in filename or "/" in filename:
            return PlainTextResponse("Invalid path", status_code=400)
        if not workspace_dir:
            return PlainTextResponse("Artifacts not configured", status_code=404)
        path = Path(workspace_dir) / ".a2a_artifacts" / task_id / filename
        try:
            path = path.resolve()
            root = Path(workspace_dir).resolve() / ".a2a_artifacts"
            if not str(path).startswith(str(root)) or not path.is_file():
                return PlainTextResponse("Not found", status_code=404)
        except Exception:
            return PlainTextResponse("Not found", status_code=404)
        return FileResponse(path, filename=filename)

    async def jsonrpc_handler(request: Request) -> Response:
        if request.method != "POST":
            return JSONResponse(
                {"error": "Method Not Allowed"},
                status_code=405,
            )
        unauth = _check_auth(request)
        if unauth is not None:
            return unauth
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return JSONResponse(
                jsonrpc_error(PARSE_ERROR, "Content-Type must be application/json", None),
                status_code=400,
            )
        try:
            body = await request.json()
        except json.JSONDecodeError as e:
            return JSONResponse(
                jsonrpc_error(PARSE_ERROR, f"Invalid JSON: {e}", None),
                status_code=400,
            )
        if not isinstance(body, dict):
            return JSONResponse(
                jsonrpc_error(INVALID_REQUEST, "Request body must be a JSON object", None),
                status_code=400,
            )
        req: JsonRpcRequest = body
        if req.get("jsonrpc") != "2.0" or "method" not in req:
            return JSONResponse(
                jsonrpc_error(INVALID_REQUEST, "Invalid JSON-RPC 2.0 request", req.get("id")),
                status_code=400,
            )
        method = req.get("method")
        params = req.get("params") if isinstance(req.get("params"), dict) else {}
        # tasks/sendSubscribe: return SSE stream (run task then push one event with result)
        if method == "tasks/sendSubscribe":
            if not params:
                return JSONResponse(
                    jsonrpc_error(-32602, "params required", req.get("id")),
                    status_code=400,
                )
            async def sse_stream():
                async for chunk in handle_tasks_send_subscribe_stream(
                    params, agent_run, task_store, workspace_dir, base_url
                ):
                    yield chunk
            return StreamingResponse(
                sse_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )
        try:
            response = await dispatch_request(
                req, agent_run, task_store, workspace_dir, base_url
            )
        except Exception as e:
            logger.exception("dispatch_request failed")
            response = jsonrpc_error(-32603, str(e), req.get("id"))
        return JSONResponse(response)

    routes = [
        Route("/.well-known/agent.json", well_known_agent, methods=["GET"]),
        Route("/", jsonrpc_handler, methods=["POST"]),
        Route("/a2a/artifacts/{task_id}/{filename}", serve_artifact, methods=["GET"]),
    ]
    return Starlette(debug=False, routes=routes)
