"""Tool-domain deterministic action handlers."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.tool import IToolManager
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalMatcherKind,
    ApprovalScope,
    ApprovalRule,
    PendingApprovalRequest,
    ToolApprovalManager,
)
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler


class IToolCatalog(Protocol):
    """Minimal tool catalog contract required by interaction actions."""

    def list_capabilities(self) -> list[Any]:
        """Return registered capability descriptors."""


class ToolsActionHandler(IActionHandler):
    """Handle deterministic tool-domain actions."""

    def __init__(self, tool_manager: IToolManager) -> None:
        self._tool_manager = tool_manager

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.TOOLS_LIST}

    # noinspection PyMethodOverriding
    async def invoke(
        self,
        action: ResourceAction,
        **_params: Any,
    ) -> Any:
        if action == ResourceAction.TOOLS_LIST:
            return self._tools_list()
        raise ValueError(f"unsupported tools action: {action.value}")

    def _tools_list(self) -> dict[str, Any]:
        tools = []
        for cap in self._tool_manager.list_capabilities():
            tools.append(_capability_to_dict(cap))
        return {"tools": tools}


class ApprovalsActionHandler(IActionHandler):
    """Handle deterministic approval-domain actions."""

    def __init__(self, approval_manager: ToolApprovalManager) -> None:
        self._approval_manager = approval_manager

    def supports(self) -> set[ResourceAction]:
        return {
            ResourceAction.APPROVALS_LIST,
            ResourceAction.APPROVALS_POLL,
            ResourceAction.APPROVALS_GRANT,
            ResourceAction.APPROVALS_DENY,
            ResourceAction.APPROVALS_REVOKE,
        }

    # noinspection PyMethodOverriding
    async def invoke(
        self,
        action: ResourceAction,
        **params: Any,
    ) -> Any:
        if action == ResourceAction.APPROVALS_LIST:
            pending = [_pending_to_dict(item) for item in self._approval_manager.list_pending()]
            rules = [_rule_to_dict(item) for item in self._approval_manager.list_rules()]
            return {"pending": pending, "rules": rules}

        if action == ResourceAction.APPROVALS_POLL:
            timeout_seconds = _parse_timeout_seconds(params)
            session_id = _optional_session_id(params.get("session_id"))
            request = await self._approval_manager.poll_pending(
                timeout_seconds=timeout_seconds,
                session_id=session_id,
            )
            return {"request": _pending_to_dict(request) if request is not None else None}

        if action == ResourceAction.APPROVALS_GRANT:
            request_id = _require_request_id(params)
            scope = _parse_scope(params.get("scope"), default=ApprovalScope.WORKSPACE)
            matcher = _parse_matcher(params.get("matcher"), default=ApprovalMatcherKind.EXACT_PARAMS)
            matcher_value = _optional_matcher_value(params.get("matcher_value"))
            actor_session_id = _optional_session_id(params.get("session_id"))
            if actor_session_id is not None and scope != ApprovalScope.SESSION:
                raise ValueError("session_id is only valid for scope=session")
            rule = await self._approval_manager.grant(
                request_id,
                scope=scope,
                matcher=matcher,
                matcher_value=matcher_value,
                actor_session_id=actor_session_id,
            )
            return {
                "request_id": request_id,
                "decision": "allow",
                "scope": scope.value,
                "matcher": matcher.value,
                "rule": _rule_to_dict(rule) if rule is not None else None,
            }

        if action == ResourceAction.APPROVALS_DENY:
            request_id = _require_request_id(params)
            scope = _parse_scope(params.get("scope"), default=ApprovalScope.ONCE)
            matcher = _parse_matcher(params.get("matcher"), default=ApprovalMatcherKind.EXACT_PARAMS)
            matcher_value = _optional_matcher_value(params.get("matcher_value"))
            actor_session_id = _optional_session_id(params.get("session_id"))
            if actor_session_id is not None and scope != ApprovalScope.SESSION:
                raise ValueError("session_id is only valid for scope=session")
            rule = await self._approval_manager.deny(
                request_id,
                scope=scope,
                matcher=matcher,
                matcher_value=matcher_value,
                actor_session_id=actor_session_id,
            )
            return {
                "request_id": request_id,
                "decision": "deny",
                "scope": scope.value,
                "matcher": matcher.value,
                "rule": _rule_to_dict(rule) if rule is not None else None,
            }

        if action == ResourceAction.APPROVALS_REVOKE:
            rule_id = _require_rule_id(params)
            removed = await self._approval_manager.revoke(rule_id)
            return {"rule_id": rule_id, "removed": removed}

        raise ValueError(f"unsupported approvals action: {action.value}")


def _capability_to_dict(cap: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("id", "type", "name", "description", "input_schema", "output_schema", "metadata"):
        if hasattr(cap, key):
            val = getattr(cap, key)
            out[key] = val.value if hasattr(val, "value") else val
    return out


def _pending_to_dict(request: PendingApprovalRequest) -> dict[str, Any]:
    return request.to_dict()


def _rule_to_dict(rule: ApprovalRule) -> dict[str, Any]:
    return rule.to_dict()


def _require_request_id(params: dict[str, Any]) -> str:
    request_id = params.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id is required")
    return request_id.strip()


def _require_rule_id(params: dict[str, Any]) -> str:
    rule_id = params.get("rule_id")
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError("rule_id is required")
    return rule_id.strip()


def _parse_scope(raw: Any, *, default: ApprovalScope) -> ApprovalScope:
    if raw is None:
        return default
    if isinstance(raw, ApprovalScope):
        return raw
    return ApprovalScope(str(raw).strip())


def _parse_matcher(raw: Any, *, default: ApprovalMatcherKind) -> ApprovalMatcherKind:
    if raw is None:
        return default
    if isinstance(raw, ApprovalMatcherKind):
        return raw
    return ApprovalMatcherKind(str(raw).strip())


def _optional_matcher_value(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _optional_session_id(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _parse_timeout_seconds(params: dict[str, Any]) -> float | None:
    raw_seconds = params.get("timeout_seconds")
    raw_millis = params.get("timeout_ms")
    if raw_seconds is not None:
        value = float(raw_seconds)
        if value < 0:
            raise ValueError("timeout_seconds must be >= 0")
        return value
    if raw_millis is not None:
        millis = float(raw_millis)
        if millis < 0:
            raise ValueError("timeout_ms must be >= 0")
        return millis / 1000.0
    return None


__all__ = ["ApprovalsActionHandler", "IToolCatalog", "ToolsActionHandler"]
