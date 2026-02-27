"""Approval command handlers."""

from __future__ import annotations

from typing import Any

from client.parser.kv import parse_key_value_args
from client.runtime.action_client import TransportActionClient
from dare_framework.transport.interaction.resource_action import ResourceAction


async def handle_approvals_tokens(
    tokens: list[str],
    *,
    action_client: TransportActionClient,
) -> dict[str, Any]:
    """Handle slash-style approvals tokens (e.g. ``['grant', 'id', 'scope=workspace']``)."""
    if not tokens:
        return {"usage": approvals_usage_lines()}
    subcommand = tokens[0].lower()
    if subcommand == "list":
        return await action_client.invoke_action(ResourceAction.APPROVALS_LIST)
    if subcommand == "poll":
        _positional, options = parse_key_value_args(tokens[1:])
        params: dict[str, Any] = {}
        if "timeout_ms" in options:
            params["timeout_ms"] = options["timeout_ms"]
        if "timeout_seconds" in options:
            params["timeout_seconds"] = options["timeout_seconds"]
        return await action_client.invoke_action(ResourceAction.APPROVALS_POLL, **params)
    if subcommand in {"grant", "deny"}:
        if len(tokens) < 2:
            raise ValueError(f"approvals {subcommand} requires request_id")
        request_id = tokens[1]
        _positional, options = parse_key_value_args(tokens[2:])
        params: dict[str, Any] = {"request_id": request_id}
        for key in ("scope", "matcher", "matcher_value", "session_id"):
            if key in options and options[key]:
                params[key] = options[key]
        action = (
            ResourceAction.APPROVALS_GRANT
            if subcommand == "grant"
            else ResourceAction.APPROVALS_DENY
        )
        return await action_client.invoke_action(action, **params)
    if subcommand == "revoke":
        if len(tokens) < 2:
            raise ValueError("approvals revoke requires rule_id")
        return await action_client.invoke_action(
            ResourceAction.APPROVALS_REVOKE,
            rule_id=tokens[1],
        )
    raise ValueError(f"unknown approvals command: {subcommand}")


def approvals_usage_lines() -> list[str]:
    return [
        "/approvals list",
        "/approvals poll [timeout_ms=30000]",
        "/approvals grant <request_id> [scope=workspace] [matcher=exact_params] [matcher_value=...] [session_id=...]",
        "/approvals deny <request_id> [scope=once] [matcher=exact_params] [matcher_value=...] [session_id=...]",
        "/approvals revoke <rule_id>",
    ]
