"""Structured payload helpers for transport interaction responses."""

from __future__ import annotations

from typing import Any


def build_success_payload(*, kind: str, target: str, resp: Any) -> dict[str, Any]:
    """Build a unified success payload for action/control/message paths."""
    return {
        "type": "result",
        "kind": kind,
        "target": target,
        "ok": True,
        "resp": resp,
    }


def build_error_payload(*, kind: str, target: str, code: str, reason: str) -> dict[str, Any]:
    """Build a unified error payload with deterministic error fields."""
    detail = {"code": code, "reason": reason}
    return {
        "type": "error",
        "kind": kind,
        "target": target,
        "ok": False,
        "code": code,
        "reason": reason,
        "error": reason,
        "resp": detail,
    }


__all__ = ["build_success_payload", "build_error_payload"]
