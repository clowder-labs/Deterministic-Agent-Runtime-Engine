"""Approval memory and pending-approval coordination for tool invocations."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from dare_framework.tool._internal.runtime_context_override import (
    RUNTIME_CONTEXT_PARAM,
    RuntimeContextOverride,
)


class ApprovalDecision(StrEnum):
    """Approval decisions returned by approval policies."""

    ALLOW = "allow"
    DENY = "deny"


class ApprovalScope(StrEnum):
    """Lifetime scope for an approval rule."""

    ONCE = "once"
    SESSION = "session"
    WORKSPACE = "workspace"
    USER = "user"


class ApprovalMatcherKind(StrEnum):
    """Supported matcher strategies for approval rules."""

    CAPABILITY = "capability"
    EXACT_PARAMS = "exact_params"
    COMMAND_PREFIX = "command_prefix"


class ApprovalEvaluationStatus(StrEnum):
    """Evaluation status for approval-required invocation checks."""

    ALLOW = "allow"
    DENY = "deny"
    PENDING = "pending"


@dataclass(frozen=True)
class ApprovalRule:
    """A persisted or in-memory approval rule."""

    rule_id: str
    capability_id: str
    decision: ApprovalDecision
    scope: ApprovalScope
    matcher: ApprovalMatcherKind
    matcher_value: str | None = None
    created_at: float = field(default_factory=time.time)
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "capability_id": self.capability_id,
            "decision": self.decision.value,
            "scope": self.scope.value,
            "matcher": self.matcher.value,
            "matcher_value": self.matcher_value,
            "created_at": self.created_at,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRule | None:
        try:
            rule_id = str(data["rule_id"])
            capability_id = str(data["capability_id"])
            decision = ApprovalDecision(str(data["decision"]))
            scope = ApprovalScope(str(data["scope"]))
            matcher = ApprovalMatcherKind(str(data["matcher"]))
        except (KeyError, TypeError, ValueError):
            return None

        matcher_value = data.get("matcher_value")
        if matcher_value is not None:
            matcher_value = str(matcher_value)

        created_at_raw = data.get("created_at", time.time())
        try:
            created_at = float(created_at_raw)
        except (TypeError, ValueError):
            created_at = time.time()

        session_id = data.get("session_id")
        if session_id is not None:
            session_id = str(session_id)

        return cls(
            rule_id=rule_id,
            capability_id=capability_id,
            decision=decision,
            scope=scope,
            matcher=matcher,
            matcher_value=matcher_value,
            created_at=created_at,
            session_id=session_id,
        )


@dataclass(frozen=True)
class PendingApprovalRequest:
    """A pending approval request awaiting a decision."""

    request_id: str
    capability_id: str
    params: dict[str, Any]
    params_hash: str
    command: str | None
    session_id: str | None
    reason: str
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "capability_id": self.capability_id,
            "params": dict(self.params),
            "params_hash": self.params_hash,
            "command": self.command,
            "session_id": self.session_id,
            "reason": self.reason,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ApprovalEvaluation:
    """Result of approval evaluation for a candidate invocation."""

    status: ApprovalEvaluationStatus
    request: PendingApprovalRequest | None = None
    rule: ApprovalRule | None = None
    reason: str | None = None


@dataclass
class _PendingApproval:
    request: PendingApprovalRequest
    fingerprint: str
    # Track all sessions that are currently blocked on this deduplicated request.
    # The first requester is also recorded so session-filtered polling can match it
    # even after subsequent evaluate() calls deduplicate to the same request id.
    session_ids: set[str] = field(default_factory=set)
    event: asyncio.Event = field(default_factory=asyncio.Event)
    resolution: ApprovalDecision | None = None


class JsonApprovalRuleStore:
    """File-backed rule store for approval rules."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[ApprovalRule]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, dict):
            return []
        rules_raw = raw.get("rules", [])
        if not isinstance(rules_raw, list):
            return []

        rules: list[ApprovalRule] = []
        for item in rules_raw:
            if not isinstance(item, dict):
                continue
            rule = ApprovalRule.from_dict(item)
            if rule is not None:
                rules.append(rule)
        return rules

    def save(self, rules: list[ApprovalRule]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "rules": [rule.to_dict() for rule in rules],
        }
        self._path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )


class ToolApprovalManager:
    """Evaluates and records tool approval decisions with persistence."""

    def __init__(
        self,
        *,
        workspace_store: JsonApprovalRuleStore,
        user_store: JsonApprovalRuleStore,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        self._workspace_store = workspace_store
        self._user_store = user_store
        self._time_fn = time_fn or time.time

        self._once_rules: list[ApprovalRule] = []
        self._session_rules: list[ApprovalRule] = []
        self._workspace_rules: list[ApprovalRule] = list(self._workspace_store.load())
        self._user_rules: list[ApprovalRule] = list(self._user_store.load())

        self._pending_by_id: dict[str, _PendingApproval] = {}
        self._pending_by_fingerprint: dict[str, _PendingApproval] = {}
        self._resolved_by_id: dict[str, ApprovalDecision] = {}
        self._lock = asyncio.Lock()
        # Condition-based wakeups avoid tight loops when polling with a session filter
        # while unrelated pending requests exist.
        self._pending_state_changed = asyncio.Condition(self._lock)

    @classmethod
    def from_paths(cls, *, workspace_dir: str | Path, user_dir: str | Path) -> ToolApprovalManager:
        workspace_store = JsonApprovalRuleStore(Path(workspace_dir) / ".dare" / "approvals.json")
        user_store = JsonApprovalRuleStore(Path(user_dir) / ".dare" / "approvals.json")
        return cls(workspace_store=workspace_store, user_store=user_store)

    def list_pending(self) -> list[PendingApprovalRequest]:
        pending = [entry.request for entry in self._pending_by_id.values()]
        pending.sort(key=lambda item: (item.created_at, item.request_id))
        return pending

    async def poll_pending(
        self,
        *,
        timeout_seconds: float | None = None,
        session_id: str | None = None,
    ) -> PendingApprovalRequest | None:
        """Return the oldest pending approval request, optionally filtered by session."""
        if timeout_seconds is not None and timeout_seconds < 0:
            raise ValueError("timeout_seconds must be >= 0")

        loop = asyncio.get_running_loop()
        deadline = None if timeout_seconds is None else loop.time() + timeout_seconds

        async with self._pending_state_changed:
            while True:
                request = self._oldest_pending_locked(session_id=session_id)
                if request is not None:
                    return request

                if deadline is None:
                    await self._pending_state_changed.wait()
                    continue

                remaining = deadline - loop.time()
                if remaining <= 0:
                    return None
                try:
                    await asyncio.wait_for(self._pending_state_changed.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    return None

    def list_rules(self) -> list[ApprovalRule]:
        combined = [
            *self._once_rules,
            *self._session_rules,
            *self._workspace_rules,
            *self._user_rules,
        ]
        return sorted(combined, key=lambda rule: rule.created_at)

    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        approval_params = _sanitize_approval_params(params)
        params_hash = _params_hash(approval_params)
        command = _extract_command(approval_params)
        fingerprint = _request_fingerprint(capability_id, params_hash)

        # Use the condition lock consistently for pending-state mutations.
        async with self._pending_state_changed:
            matched_rule = self._find_matching_rule(
                capability_id=capability_id,
                params_hash=params_hash,
                command=command,
                session_id=session_id,
            )
            if matched_rule is not None:
                if matched_rule.scope == ApprovalScope.ONCE:
                    self._remove_rule(matched_rule.rule_id)
                if matched_rule.decision == ApprovalDecision.ALLOW:
                    return ApprovalEvaluation(
                        status=ApprovalEvaluationStatus.ALLOW,
                        rule=matched_rule,
                        reason="matched allow rule",
                    )
                return ApprovalEvaluation(
                    status=ApprovalEvaluationStatus.DENY,
                    rule=matched_rule,
                    reason="matched deny rule",
                )

            existing = self._pending_by_fingerprint.get(fingerprint)
            if existing is None:
                request = PendingApprovalRequest(
                    request_id=uuid4().hex,
                    capability_id=capability_id,
                    params=dict(approval_params),
                    params_hash=params_hash,
                    command=command,
                    session_id=session_id,
                    reason=reason,
                    created_at=self._time_fn(),
                )
                existing = _PendingApproval(request=request, fingerprint=fingerprint)
                self._track_pending_session_locked(existing, session_id)
                self._pending_by_fingerprint[fingerprint] = existing
                self._pending_by_id[request.request_id] = existing
                self._pending_state_changed.notify_all()
            else:
                # A deduplicated request can gain new interested sessions later.
                # Wake session-filtered poll waiters when that subscriber set expands.
                added_session = self._track_pending_session_locked(existing, session_id)
                if added_session:
                    self._pending_state_changed.notify_all()

            return ApprovalEvaluation(
                status=ApprovalEvaluationStatus.PENDING,
                request=existing.request,
                reason="approval required",
            )

    async def wait_for_resolution(
        self,
        request_id: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ApprovalDecision:
        # Keep all pending/resolution map access on the same condition-backed lock
        # so concurrency audits only need to reason about one synchronization surface.
        async with self._pending_state_changed:
            resolved = self._resolved_by_id.pop(request_id, None)
            if resolved is not None:
                return resolved
            pending = self._pending_by_id.get(request_id)
        if pending is None:
            raise KeyError(f"Unknown approval request: {request_id}")

        wait_target = pending.event.wait()
        if timeout_seconds is None:
            await wait_target
        else:
            await asyncio.wait_for(wait_target, timeout=timeout_seconds)

        if pending.resolution is None:
            raise RuntimeError(f"Approval request resolved without decision: {request_id}")
        async with self._pending_state_changed:
            self._resolved_by_id.pop(request_id, None)
        return pending.resolution

    async def grant(
        self,
        request_id: str,
        *,
        scope: ApprovalScope,
        matcher: ApprovalMatcherKind,
        matcher_value: str | None = None,
        actor_session_id: str | None = None,
    ) -> ApprovalRule | None:
        return await self._resolve_request(
            request_id=request_id,
            decision=ApprovalDecision.ALLOW,
            scope=scope,
            matcher=matcher,
            matcher_value=matcher_value,
            actor_session_id=actor_session_id,
        )

    async def deny(
        self,
        request_id: str,
        *,
        scope: ApprovalScope,
        matcher: ApprovalMatcherKind,
        matcher_value: str | None = None,
        actor_session_id: str | None = None,
    ) -> ApprovalRule | None:
        return await self._resolve_request(
            request_id=request_id,
            decision=ApprovalDecision.DENY,
            scope=scope,
            matcher=matcher,
            matcher_value=matcher_value,
            actor_session_id=actor_session_id,
        )

    async def revoke(self, rule_id: str) -> bool:
        async with self._pending_state_changed:
            removed = self._remove_rule(rule_id)
            if removed:
                self._persist_rules_for_scope(removed.scope)
            return removed is not None

    async def _resolve_request(
        self,
        *,
        request_id: str,
        decision: ApprovalDecision,
        scope: ApprovalScope,
        matcher: ApprovalMatcherKind,
        matcher_value: str | None,
        actor_session_id: str | None = None,
    ) -> ApprovalRule | None:
        # Keep pending-state transitions on the condition lock to avoid mixed styles.
        async with self._pending_state_changed:
            pending = self._pending_by_id.get(request_id)
            if pending is None:
                raise KeyError(f"Unknown approval request: {request_id}")

            request = pending.request
            rule = self._build_rule(
                request=request,
                decision=decision,
                scope=scope,
                matcher=matcher,
                matcher_value=matcher_value,
                actor_session_id=actor_session_id,
            )
            if rule is not None:
                self._append_rule(rule)
                self._persist_rules_for_scope(rule.scope)

            pending.resolution = decision
            pending.event.set()
            self._resolved_by_id[request_id] = decision
            self._pending_by_id.pop(request_id, None)
            self._pending_by_fingerprint.pop(pending.fingerprint, None)
            self._pending_state_changed.notify_all()
            return rule

    def _append_rule(self, rule: ApprovalRule) -> None:
        if rule.scope == ApprovalScope.ONCE:
            self._once_rules.append(rule)
        elif rule.scope == ApprovalScope.SESSION:
            self._session_rules.append(rule)
        elif rule.scope == ApprovalScope.WORKSPACE:
            self._workspace_rules.append(rule)
        elif rule.scope == ApprovalScope.USER:
            self._user_rules.append(rule)

    def _build_rule(
        self,
        *,
        request: PendingApprovalRequest,
        decision: ApprovalDecision,
        scope: ApprovalScope,
        matcher: ApprovalMatcherKind,
        matcher_value: str | None,
        actor_session_id: str | None,
    ) -> ApprovalRule | None:
        # ONCE only applies to the current pending request, no reusable rule needed.
        if scope == ApprovalScope.ONCE:
            return None

        normalized_value = matcher_value
        if matcher == ApprovalMatcherKind.EXACT_PARAMS:
            normalized_value = request.params_hash
        elif matcher == ApprovalMatcherKind.COMMAND_PREFIX:
            normalized_value = (matcher_value or request.command or "").strip()
            if not normalized_value:
                raise ValueError("command_prefix matcher requires matcher_value or command input")
        else:
            normalized_value = None

        return ApprovalRule(
            rule_id=uuid4().hex,
            capability_id=request.capability_id,
            decision=decision,
            scope=scope,
            matcher=matcher,
            matcher_value=normalized_value,
            created_at=self._time_fn(),
            session_id=(actor_session_id or request.session_id) if scope == ApprovalScope.SESSION else None,
        )

    def _persist_rules_for_scope(self, scope: ApprovalScope) -> None:
        if scope == ApprovalScope.WORKSPACE:
            self._workspace_store.save(self._workspace_rules)
        elif scope == ApprovalScope.USER:
            self._user_store.save(self._user_rules)

    def _remove_rule(self, rule_id: str) -> ApprovalRule | None:
        for bucket in (self._once_rules, self._session_rules, self._workspace_rules, self._user_rules):
            for idx, rule in enumerate(bucket):
                if rule.rule_id == rule_id:
                    return bucket.pop(idx)
        return None

    def _find_matching_rule(
        self,
        *,
        capability_id: str,
        params_hash: str,
        command: str | None,
        session_id: str | None,
    ) -> ApprovalRule | None:
        ordered_rules: list[ApprovalRule] = []
        ordered_rules.extend(self._once_rules)
        ordered_rules.extend(
            [rule for rule in self._session_rules if rule.session_id is None or rule.session_id == session_id]
        )
        ordered_rules.extend(self._workspace_rules)
        ordered_rules.extend(self._user_rules)

        matches = [
            rule
            for rule in ordered_rules
            if _rule_matches(rule, capability_id=capability_id, params_hash=params_hash, command=command)
        ]
        for rule in matches:
            if rule.decision == ApprovalDecision.DENY:
                return rule
        for rule in matches:
            if rule.decision == ApprovalDecision.ALLOW:
                return rule
        return None

    def _oldest_pending_locked(self, *, session_id: str | None = None) -> PendingApprovalRequest | None:
        if not self._pending_by_id:
            return None
        candidates = list(self._pending_by_id.values())
        if session_id is not None:
            candidates = [
                item
                for item in candidates
                if session_id in item.session_ids or item.request.session_id == session_id
            ]
            if not candidates:
                return None
        oldest = min(
            candidates,
            key=lambda item: (item.request.created_at, item.request.request_id),
        )
        return oldest.request

    @staticmethod
    def _track_pending_session_locked(pending: _PendingApproval, session_id: str | None) -> bool:
        if isinstance(session_id, str) and session_id:
            if session_id in pending.session_ids:
                return False
            pending.session_ids.add(session_id)
            return True
        return False


def _rule_matches(
    rule: ApprovalRule,
    *,
    capability_id: str,
    params_hash: str,
    command: str | None,
) -> bool:
    if rule.capability_id != capability_id:
        return False

    if rule.matcher == ApprovalMatcherKind.CAPABILITY:
        return True
    if rule.matcher == ApprovalMatcherKind.EXACT_PARAMS:
        return bool(rule.matcher_value) and rule.matcher_value == params_hash
    if rule.matcher == ApprovalMatcherKind.COMMAND_PREFIX:
        if not rule.matcher_value:
            return False
        if not isinstance(command, str):
            return False
        prefix = rule.matcher_value.strip()
        normalized = command.strip()
        return normalized == prefix or normalized.startswith(prefix + " ")
    return False


def _params_hash(params: dict[str, Any]) -> str:
    canonical = json.dumps(_normalize_value(params), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _extract_command(params: dict[str, Any]) -> str | None:
    command = params.get("command")
    if isinstance(command, str) and command.strip():
        return command.strip()
    return None


def _sanitize_approval_params(params: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in params.items():
        if key == RUNTIME_CONTEXT_PARAM:
            # Internal override transport never participates in approval matching.
            # It is internal runtime control data that should not affect dedupe.
            continue
        if isinstance(value, RuntimeContextOverride):
            # Defensive: collapse internal marker to raw context when seen.
            value = value.context
        normalized[key] = value
    return normalized


def _request_fingerprint(capability_id: str, params_hash: str) -> str:
    return f"{capability_id}:{params_hash}"


__all__ = [
    "ApprovalDecision",
    "ApprovalEvaluation",
    "ApprovalEvaluationStatus",
    "ApprovalMatcherKind",
    "ApprovalRule",
    "ApprovalScope",
    "JsonApprovalRuleStore",
    "PendingApprovalRequest",
    "ToolApprovalManager",
]
