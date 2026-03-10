"""A2A Message/Part <-> DARE context and RunResult (a2acn.com/docs/concepts/message)."""

from __future__ import annotations

import base64
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from dare_framework.a2a.types import PartDict, text_part, file_part_inline, file_part_uri
from dare_framework.context import Message
from dare_framework.context.types import AttachmentKind, AttachmentRef, MessageKind, MessageRole
from dare_framework.plan.types import RunResult


def message_parts_to_user_input(parts: list[PartDict]) -> str:
    """Extract a single user input string from A2A message parts for DARE task description.

    Text parts are concatenated; file parts are summarized by filename (inline content
    is not passed as file to agent in this minimal path - only text is used as task description).
    """
    segments: list[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        kind = p.get("type")
        if kind == "text":
            segments.append((p.get("text") or "").strip())
        elif kind == "file":
            filename = p.get("filename") or p.get("uri") or "file"
            segments.append(f"[Attachment: {filename}]")
    return "\n".join(s for s in segments if s).strip() or ""


def _is_image_attachment(*, mime_type: str | None, filename: str | None, uri: str | None = None) -> bool:
    """Return whether a resolved A2A file part should become a canonical image attachment."""
    normalized_mime = mime_type.strip().lower() if isinstance(mime_type, str) else ""
    if normalized_mime.startswith("image/"):
        return True
    candidate_name = filename or uri or ""
    guessed, _ = mimetypes.guess_type(candidate_name)
    return bool(guessed and guessed.startswith("image/"))


def _build_inline_attachment_uri(
    *, mime_type: str | None, filename: str | None, data_b64: str | None
) -> str | None:
    """Build a provider-valid data URI for inline image transport."""
    if not isinstance(data_b64, str) or not data_b64.strip():
        return None
    normalized_mime = (mime_type or "").strip()
    guessed_mime = mimetypes.guess_type(filename or "")[0] if filename else None
    media_type = normalized_mime or guessed_mime or "application/octet-stream"
    return f"data:{media_type};base64,{data_b64.strip()}"


def _is_provider_valid_attachment_uri(uri: str | None) -> bool:
    """Keep canonical attachment URIs limited to provider-safe URI schemes."""
    if not isinstance(uri, str) or not uri.strip():
        return False
    parsed = urlparse(uri.strip())
    return parsed.scheme in {"http", "https", "data"}


def _decode_inline_file_part(p: dict[str, Any], dest_dir: Path) -> dict[str, Any] | None:
    """Decode FilePart with inlineData to a file under dest_dir. Returns {path, filename, mimeType} or None."""
    inline = p.get("inlineData")
    if not isinstance(inline, dict):
        return None
    data_b64 = inline.get("data")
    if not data_b64:
        return None
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except Exception:
        return None
    filename = p.get("filename") or "attachment"
    # Sanitize filename
    filename = os.path.basename(filename) or "attachment"
    inline_mime = inline.get("mimeType") if isinstance(inline.get("mimeType"), str) else None
    mime = p.get("mimeType") or inline_mime or "application/octet-stream"
    path = dest_dir / filename
    if path.exists():
        path = dest_dir / f"{uuid4().hex}_{filename}"
    path.write_bytes(raw)
    return {"path": str(path.resolve()), "filename": filename, "mimeType": mime}


def _describe_uri_file_part(p: dict[str, Any]) -> dict[str, Any] | None:
    """Describe a provider-safe URI file part without dereferencing it server-side."""
    uri = p.get("uri")
    if not isinstance(uri, str) or not _is_provider_valid_attachment_uri(uri):
        return None
    parsed = urlparse(uri)
    filename = p.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        filename = os.path.basename(uri.split("?")[0]) if parsed.scheme != "data" else "attachment"
    filename = os.path.basename(filename) or "attachment"
    explicit_mime = p.get("mimeType") if isinstance(p.get("mimeType"), str) else None
    uri_mime: str | None = None
    # For data URIs, MIME type is encoded in the URI header and must be
    # considered for image classification when caller does not provide mimeType.
    if parsed.scheme == "data":
        header = uri[5:].split(",", 1)[0]
        media_type = header.split(";", 1)[0].strip().lower()
        if media_type and "/" in media_type:
            uri_mime = media_type
    mime = (
        (explicit_mime or "").strip()
        or uri_mime
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )
    return {"uri": uri, "filename": filename, "mimeType": mime}


def message_parts_to_user_input_and_attachments(
    parts: list[PartDict],
    workspace_dir: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Extract user input and attachment descriptors without remote URI downloads.

    Returns:
        (user_input_str, attachments) where attachments is a list of
        `{"path" | "uri", "filename": str, "mimeType": str}` descriptors suitable for
        `task.metadata["a2a_attachments"]`.
    """
    segments: list[str] = []
    attachments: list[dict[str, Any]] = []

    root = Path(workspace_dir) if workspace_dir else Path(tempfile.gettempdir())
    dest_dir: Path | None = None

    def ensure_dest_dir() -> Path:
        nonlocal dest_dir
        if dest_dir is None:
            dest_dir = root / ".a2a_attachments" / uuid4().hex
            dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir

    for p in parts:
        if not isinstance(p, dict):
            continue
        kind = p.get("type")
        if kind == "text":
            segments.append((p.get("text") or "").strip())
        elif kind == "file":
            if "inlineData" in p:
                att = _decode_inline_file_part(p, ensure_dest_dir())
                if att:
                    attachments.append(att)
                    segments.append(f"[Attachment: {att['path']}]")
                else:
                    segments.append(f"[Attachment: {p.get('filename') or 'file'}]")
            elif "uri" in p:
                att = _describe_uri_file_part(p)
                if att:
                    attachments.append(att)
                    segments.append(f"[Attachment: {att['uri']}]")
                else:
                    segments.append(f"[Attachment: {p.get('uri', 'file')}]")

    user_input = "\n".join(s for s in segments if s).strip() or ""
    return (user_input, attachments)


def message_parts_to_message(
    parts: list[PartDict],
    *,
    workspace_dir: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Message:
    """Convert A2A parts into a canonical DARE user message.

    Text parts stay in `Message.text`. Supported image file parts become
    `Message.attachments`; unsupported file parts degrade to textual placeholders.
    Inline file parts are materialized under `workspace_dir/.a2a_attachments/<uuid>/`.
    Provider-safe remote URIs are preserved as URIs and are not fetched server-side.
    """
    base_metadata = dict(metadata or {})
    text_segments: list[str] = []
    attachment_refs: list[AttachmentRef] = []
    resolved_attachments: list[dict[str, Any]] = []

    root = Path(workspace_dir) if workspace_dir else Path(tempfile.gettempdir())
    dest_dir: Path | None = None

    def ensure_dest_dir() -> Path:
        nonlocal dest_dir
        if dest_dir is None:
            dest_dir = root / ".a2a_attachments" / uuid4().hex
            dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir

    for part in parts:
        if not isinstance(part, dict):
            continue
        kind = part.get("type")
        if kind == "text":
            segment = (part.get("text") or "").strip()
            if segment:
                text_segments.append(segment)
            continue
        if kind != "file":
            continue

        resolved: dict[str, Any] | None = None
        attachment_uri: str | None = None
        if "inlineData" in part:
            resolved = _decode_inline_file_part(part, ensure_dest_dir())
            inline = part.get("inlineData")
            # Preserve only caller-supplied MIME for URI construction.
            # Do not pass decode-time defaults (application/octet-stream),
            # otherwise filename-based inference can never apply.
            raw_mime = ""
            if isinstance(part.get("mimeType"), str):
                raw_mime = str(part.get("mimeType") or "").strip()
            elif isinstance(inline, dict) and isinstance(inline.get("mimeType"), str):
                raw_mime = str(inline.get("mimeType") or "").strip()
            attachment_uri = _build_inline_attachment_uri(
                mime_type=raw_mime,
                filename=str(part.get("filename") or (resolved or {}).get("filename") or "") or None,
                data_b64=inline.get("data") if isinstance(inline, dict) else None,
            )
        elif "uri" in part:
            resolved = _describe_uri_file_part(part)
            if resolved is not None:
                attachment_uri = str(resolved["uri"])

        if resolved is not None:
            resolved_attachments.append(resolved)
            if _is_image_attachment(
                mime_type=resolved.get("mimeType"),
                filename=resolved.get("filename"),
                uri=attachment_uri or resolved.get("path") or resolved.get("uri"),
            ):
                # Keep model-facing attachment URIs provider-valid; local temp paths
                # remain available only through metadata for audit/debugging.
                if attachment_uri is not None:
                    attachment_refs.append(
                        AttachmentRef(
                            kind=AttachmentKind.IMAGE,
                            uri=attachment_uri,
                            mime_type=str(resolved.get("mimeType") or "") or None,
                            filename=str(resolved.get("filename") or "") or None,
                        )
                    )
                    continue

        label = (
            (resolved or {}).get("filename")
            or part.get("filename")
            or part.get("uri")
            or "file"
        )
        text_segments.append(f"[Attachment: {label}]")

    if resolved_attachments:
        base_metadata["a2a_attachments"] = resolved_attachments

    text_value = "\n".join(segment for segment in text_segments if segment).strip() or None
    return Message(
        role=MessageRole.USER,
        kind=MessageKind.CHAT,
        text=text_value,
        attachments=attachment_refs,
        metadata=base_metadata,
    )


def message_parts_to_artifact_parts(parts: list[PartDict]) -> list[PartDict]:
    """Pass-through: parts from agent message/artifact stay as Part dicts (for building Artifact)."""
    return [dict(p) for p in parts if isinstance(p, dict)]


def _safe_artifact_filename(name: str) -> str:
    """Return a safe filename for artifact storage (no path components)."""
    base = os.path.basename(name)
    if not base or base in (".", ".."):
        return "file"
    return base


def run_result_to_artifact_parts(
    result: RunResult,
    *,
    max_inline_bytes: int = 1 << 20,
    task_id: str | None = None,
    base_url: str | None = None,
    workspace_dir: str | None = None,
) -> list[PartDict]:
    """Convert DARE RunResult to A2A Artifact parts (text + optional file parts from metadata).

    If result.metadata has "a2a_output_files" (list of paths or list of {path, filename?, mimeType?}):
    - size <= max_inline_bytes: FilePart inline (base64).
    - size > max_inline_bytes and task_id/base_url/workspace_dir set: copy to workspace_dir/.a2a_artifacts/
      <task_id>/<filename> and add FilePart with uri = base_url/a2a/artifacts/<task_id>/<filename>.
    """
    import shutil
    from urllib.parse import quote

    out_parts: list[PartDict] = []
    text = result.output_text
    if text is None and result.output is not None:
        text = result.output
        if not isinstance(text, str):
            text = str(text)
    if text is not None:
        if text.strip():
            out_parts.append(text_part(text.strip()))
    if result.errors:
        out_parts.append(text_part("Errors:\n" + "\n".join(result.errors)))

    files = result.metadata.get("a2a_output_files") if isinstance(result.metadata, dict) else None
    if not isinstance(files, list):
        return out_parts

    can_serve_uri = task_id and base_url and workspace_dir
    artifacts_root = Path(workspace_dir) / ".a2a_artifacts" / (task_id or "") if can_serve_uri else None

    for entry in files:
        if isinstance(entry, str):
            path_str, filename, mime = entry, Path(entry).name, "application/octet-stream"
        elif isinstance(entry, dict):
            path_str = entry.get("path")
            if not path_str:
                continue
            filename = entry.get("filename") or Path(path_str).name
            mime = entry.get("mimeType") or "application/octet-stream"
        else:
            continue
        path = Path(path_str)
        if not path.is_file():
            continue
        size = path.stat().st_size
        filename_safe = _safe_artifact_filename(filename)
        if size <= max_inline_bytes:
            try:
                raw = path.read_bytes()
                b64 = base64.b64encode(raw).decode("ascii")
                out_parts.append(file_part_inline(mime, filename_safe, b64))
            except Exception:
                pass
        elif can_serve_uri and artifacts_root is not None:
            try:
                artifacts_root.mkdir(parents=True, exist_ok=True)
                dest = artifacts_root / filename_safe
                if dest != path.resolve():
                    shutil.copy2(path, dest)
                uri = f"{base_url.rstrip('/')}/a2a/artifacts/{task_id}/{quote(filename_safe)}"
                out_parts.append(file_part_uri(mime, filename_safe, uri))
            except Exception:
                pass
    return out_parts


def run_result_to_artifact_dict(
    result: RunResult,
    *,
    artifact_id: str | None = None,
    name: str = "result",
    max_inline_bytes: int = 1 << 20,
    task_id: str | None = None,
    base_url: str | None = None,
    workspace_dir: str | None = None,
) -> dict[str, Any]:
    """Build a single A2A Artifact from RunResult (text + optional a2a_output_files from metadata)."""
    parts = run_result_to_artifact_parts(
        result,
        max_inline_bytes=max_inline_bytes,
        task_id=task_id,
        base_url=base_url,
        workspace_dir=workspace_dir,
    )
    artifact: dict[str, Any] = {"name": name, "parts": parts}
    if artifact_id:
        artifact["artifactId"] = artifact_id
    return artifact
