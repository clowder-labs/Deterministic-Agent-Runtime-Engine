"""Structured payload helpers for transport interaction responses."""

from __future__ import annotations

from dare_framework.transport.types import SelectPayload


def build_approval_pending_payload(
    *,
    request: dict[str, Any],
    capability_id: str,
    tool_name: str,
    tool_call_id: str,
) -> SelectPayload:
    """Build a transport payload for a pending tool approval request."""
    prompt = request.get("reason")
    if not isinstance(prompt, str) or not prompt.strip():
        prompt = f"Tool {tool_name} requires approval"
    return SelectPayload(
        id=str(request.get("request_id") or tool_call_id or capability_id),
        select_kind="ask",
        select_domain="approval",
        prompt=prompt,
        options=[
            {"label": "allow", "description": "Approve this tool invocation."},
            {"label": "deny", "description": "Deny this tool invocation."},
        ],
        metadata={
            "request": request,
            "capability_id": capability_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
        },
    )


def build_approval_resolved_payload(
    *,
    request_id: str,
    decision: str,
    capability_id: str,
    tool_name: str,
    tool_call_id: str,
) -> SelectPayload:
    """Build a transport payload for a resolved tool approval request."""
    return SelectPayload(
        id=request_id,
        select_kind="answered",
        select_domain="approval",
        selected={
            "request_id": request_id,
            "decision": decision,
        },
        metadata={
            "capability_id": capability_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
        },
    )


__all__ = [
    "build_approval_pending_payload",
    "build_approval_resolved_payload",
]
