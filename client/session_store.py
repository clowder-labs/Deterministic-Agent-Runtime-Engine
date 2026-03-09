"""Persistent CLI session snapshot storage."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from client.session import CLISessionState, ExecutionMode
from dare_framework.context import AttachmentRef, Message, MessageKind, MessageMark, MessageRole

SESSION_SNAPSHOT_SCHEMA_VERSION = "client-session.v1"
LATEST_SESSION_ALIAS = "latest"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class SessionStoreError(ValueError):
    """Raised when CLI session snapshots cannot be loaded or validated."""


@dataclass(frozen=True)
class SessionSnapshot:
    """Serialized session state that can be restored into a fresh runtime."""

    session_id: str
    mode: ExecutionMode
    created_at: float
    updated_at: float
    workspace_dir: str
    messages: list[Message]


@dataclass(frozen=True)
class SessionListing:
    """Summary row returned by session discovery APIs."""

    session_id: str
    mode: ExecutionMode
    created_at: float
    updated_at: float
    workspace_dir: str
    messages_count: int
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace_dir": self.workspace_dir,
            "messages_count": self.messages_count,
            "path": self.path,
        }


def _json_safe(value: Any, *, _seen: set[int] | None = None) -> Any:
    """Best-effort conversion for JSON persistence."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list, tuple, set)):
        marker = id(value)
        if marker in _seen:
            return "<circular>"
        _seen.add(marker)
    if isinstance(value, dict):
        try:
            return {str(key): _json_safe(item, _seen=_seen) for key, item in value.items()}
        finally:
            _seen.remove(marker)
    if isinstance(value, set):
        try:
            normalized = [_json_safe(item, _seen=_seen) for item in value]
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        finally:
            _seen.remove(marker)
    if isinstance(value, (list, tuple)):
        try:
            return [_json_safe(item, _seen=_seen) for item in value]
        finally:
            _seen.remove(marker)
    return str(value)


class ClientSessionStore:
    """Workspace-scoped file-backed session snapshot store."""

    def __init__(self, workspace_dir: str | Path) -> None:
        self._workspace_dir = Path(workspace_dir).expanduser().resolve()
        self._session_dir = self._workspace_dir / ".dare" / "sessions"
        self._session_dir.mkdir(parents=True, exist_ok=True)

    @property
    def session_dir(self) -> Path:
        return self._session_dir

    def path_for(self, session_id: str) -> Path:
        normalized = self._normalize_session_id(session_id)
        path = (self._session_dir / f"{normalized}.json").resolve()
        session_root = self._session_dir.resolve()
        if not path.is_relative_to(session_root):
            raise SessionStoreError(f"invalid session_id path traversal: {normalized}")
        return path

    def save(self, *, state: CLISessionState, messages: list[Message]) -> Path:
        """Persist the current CLI session snapshot."""
        session_id = self._normalize_session_id(state.conversation_id)
        path = self.path_for(session_id)
        created_at = time.time()
        if path.exists():
            try:
                created_at = self._load_path(path).created_at
            except SessionStoreError:
                # Prefer forward progress: overwrite an unreadable older snapshot.
                created_at = time.time()
        payload = {
            "schema_version": SESSION_SNAPSHOT_SCHEMA_VERSION,
            "session_id": session_id,
            "mode": state.mode.value,
            "created_at": created_at,
            "updated_at": time.time(),
            "workspace_dir": str(self._workspace_dir),
            "messages": [self._message_to_dict(message) for message in messages],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, resume_target: str) -> SessionSnapshot:
        """Load a persisted session snapshot by explicit id or ``latest``."""
        normalized = (resume_target or "").strip() or LATEST_SESSION_ALIAS
        if normalized == LATEST_SESSION_ALIAS:
            return self._load_latest()
        path = self.path_for(normalized)
        if not path.exists():
            raise SessionStoreError(f"resume target not found: {normalized}")
        return self._load_path(path)

    def _load_latest(self) -> SessionSnapshot:
        candidates: list[SessionSnapshot] = []
        first_error: SessionStoreError | None = None
        for path in sorted(self._session_dir.glob("*.json")):
            try:
                candidates.append(self._load_path(path))
            except SessionStoreError as exc:
                if first_error is None:
                    first_error = exc
        if not candidates:
            if first_error is not None:
                raise first_error
            raise SessionStoreError(f"resume target not found: {LATEST_SESSION_ALIAS}")
        return max(candidates, key=lambda snapshot: snapshot.updated_at)

    def list_sessions(self) -> list[SessionListing]:
        """Return resumable sessions ordered by most-recent update first."""
        listings: list[SessionListing] = []
        for path in sorted(self._session_dir.glob("*.json")):
            try:
                snapshot = self._load_path(path)
            except SessionStoreError:
                continue
            listings.append(
                SessionListing(
                    session_id=snapshot.session_id,
                    mode=snapshot.mode,
                    created_at=snapshot.created_at,
                    updated_at=snapshot.updated_at,
                    workspace_dir=snapshot.workspace_dir,
                    messages_count=len(snapshot.messages),
                    path=str(path),
                )
            )
        return sorted(listings, key=lambda item: item.updated_at, reverse=True)

    def _load_path(self, path: Path) -> SessionSnapshot:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SessionStoreError(f"failed to read session snapshot: {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SessionStoreError(f"invalid session snapshot JSON: {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise SessionStoreError(f"invalid session snapshot payload: {path}")
        schema_version = str(raw.get("schema_version", "")).strip()
        if schema_version != SESSION_SNAPSHOT_SCHEMA_VERSION:
            raise SessionStoreError(
                "unsupported session snapshot schema_version: "
                f"{schema_version or '<missing>'}"
            )

        session_id = self._normalize_session_id(raw.get("session_id"))
        mode_raw = str(raw.get("mode", "")).strip()
        try:
            mode = ExecutionMode(mode_raw)
        except ValueError as exc:
            raise SessionStoreError(f"invalid session mode in snapshot: {path}: {mode_raw}") from exc

        created_at = self._coerce_timestamp(raw.get("created_at"), field_name="created_at", path=path)
        updated_at = self._coerce_timestamp(raw.get("updated_at"), field_name="updated_at", path=path)
        workspace_dir = str(raw.get("workspace_dir", "")).strip() or str(self._workspace_dir)
        messages_raw = raw.get("messages", [])
        if not isinstance(messages_raw, list):
            raise SessionStoreError(f"invalid messages payload in snapshot: {path}")
        messages = [self._message_from_dict(item, path=path) for item in messages_raw]
        return SessionSnapshot(
            session_id=session_id,
            mode=mode,
            created_at=created_at,
            updated_at=updated_at,
            workspace_dir=workspace_dir,
            messages=messages,
        )

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        return {
            "role": message.role.value if hasattr(message.role, "value") else str(message.role),
            "kind": message.kind.value if hasattr(message.kind, "value") else str(message.kind),
            "text": message.text,
            "attachments": [
                {
                    "kind": attachment.kind.value,
                    "uri": attachment.uri,
                    "mime_type": attachment.mime_type,
                    "filename": attachment.filename,
                    "metadata": _json_safe(dict(attachment.metadata)),
                }
                for attachment in message.attachments
            ],
            "data": _json_safe(dict(message.data or {})),
            "name": message.name,
            "metadata": _json_safe(dict(message.metadata)),
            "mark": message.mark.value if hasattr(message.mark, "value") else str(message.mark),
            "id": message.id,
        }

    def _message_from_dict(self, raw: Any, *, path: Path) -> Message:
        if not isinstance(raw, dict):
            raise SessionStoreError(f"invalid message entry in snapshot: {path}")
        mark_raw = str(raw.get("mark", MessageMark.TEMPORARY.value)).strip()
        try:
            mark = MessageMark(mark_raw)
        except ValueError:
            mark = MessageMark.TEMPORARY
        metadata_raw = raw.get("metadata", {})
        metadata = (
            {str(key): value for key, value in metadata_raw.items()}
            if isinstance(metadata_raw, dict)
            else {}
        )
        attachments_raw = raw.get("attachments", [])
        attachments = AttachmentRef.coerce_many(attachments_raw if isinstance(attachments_raw, list) else [])
        data_raw = raw.get("data")
        return Message(
            role=raw.get("role", MessageRole.USER),
            kind=raw.get("kind", MessageKind.CHAT),
            text=raw.get("text", raw.get("content")),
            attachments=attachments,
            data={str(key): value for key, value in data_raw.items()} if isinstance(data_raw, dict) else None,
            name=str(raw.get("name")) if raw.get("name") is not None else None,
            metadata=metadata,
            mark=mark,
            id=str(raw.get("id")) if raw.get("id") is not None else None,
        )

    def _normalize_session_id(self, raw: Any) -> str:
        normalized = str(raw).strip() if raw is not None else ""
        if not normalized:
            raise SessionStoreError("session_id is required")
        if not SESSION_ID_PATTERN.fullmatch(normalized):
            raise SessionStoreError(f"invalid session_id: {normalized}")
        if ".." in normalized:
            raise SessionStoreError(f"invalid session_id: {normalized}")
        return normalized

    def _coerce_timestamp(self, raw: Any, *, field_name: str, path: Path) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise SessionStoreError(f"invalid {field_name} in snapshot: {path}") from exc
