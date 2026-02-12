"""Structured payload helpers for transport interaction responses."""

from __future__ import annotations

from typing import Any


def build_success_payload(*, kind: str, target: str, resp: Any) -> dict[str, Any]:
    """Build a unified success payload for action/control/message paths."""
    return {
        "kind": kind,
        "target": target,
        "ok": True,
        "resp": resp,
    }


def build_error_payload(*, kind: str, target: str, code: str, reason: str) -> dict[str, Any]:
    """Build a unified error payload with deterministic error fields."""
    detail = {"code": code, "reason": reason}
    return {
        "kind": kind,
        "target": target,
        "ok": False,
        "code": code,
        "reason": reason,
        "error": reason,
        "resp": detail,
    }


def build_approval_pending_payload(
    *,
    request: dict[str, Any],
    capability_id: str,
    tool_name: str,
    tool_call_id: str,
) -> dict[str, Any]:
    """Build a transport payload for a pending tool approval request."""
    return {
        "kind": "approval",
        "target": capability_id,
        "ok": True,
        "resp": {
            "request": request,
            "capability_id": capability_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
        },
    }


def build_approval_resolved_payload(
    *,
    request_id: str,
    decision: str,
    capability_id: str,
    tool_name: str,
    tool_call_id: str,
) -> dict[str, Any]:
    """Build a transport payload for a resolved tool approval request."""
    return {
        "kind": "approval",
        "target": capability_id,
        "ok": True,
        "resp": {
            "request_id": request_id,
            "decision": decision,
            "capability_id": capability_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
        },
    }


__all__ = [
    "build_success_payload",
    "build_error_payload",
    "build_approval_pending_payload",
    "build_approval_resolved_payload",
]
