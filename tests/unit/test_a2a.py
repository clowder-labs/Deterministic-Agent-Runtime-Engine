"""Unit tests for dare_framework.a2a (types, message_adapter, handlers)."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import pytest

from dare_framework.a2a.types import (
    file_part_inline,
    file_part_uri,
    jsonrpc_error,
    jsonrpc_result,
    task_state,
    text_part,
)
from dare_framework.a2a.server.message_adapter import (
    message_parts_to_message,
    message_parts_to_user_input,
    message_parts_to_user_input_and_attachments,
    run_result_to_artifact_parts,
    run_result_to_artifact_dict,
)
from dare_framework.context.types import AttachmentKind, MessageKind, MessageRole
from dare_framework.plan.types import RunResult


# ----- types -----


def test_text_part() -> None:
    p = text_part("hello")
    assert p["type"] == "text"
    assert p["text"] == "hello"


def test_file_part_inline() -> None:
    p = file_part_inline("text/plain", "a.txt", "aGVsbG8=")
    assert p["type"] == "file"
    assert p["mimeType"] == "text/plain"
    assert p["filename"] == "a.txt"
    assert p["inlineData"]["data"] == "aGVsbG8="


def test_file_part_uri() -> None:
    p = file_part_uri("application/pdf", "out.pdf", "https://example.com/f/out.pdf")
    assert p["type"] == "file"
    assert p["uri"] == "https://example.com/f/out.pdf"


def test_task_state() -> None:
    s = task_state("t1", "s1", "completed", artifacts=[{"name": "a", "parts": []}])
    assert s["id"] == "t1"
    assert s["sessionId"] == "s1"
    assert s["status"]["state"] == "completed"
    assert len(s["artifacts"]) == 1


def test_jsonrpc_result() -> None:
    r = jsonrpc_result({"id": "t1"}, request_id=1)
    assert r["jsonrpc"] == "2.0"
    assert r["id"] == 1
    assert r["result"]["id"] == "t1"


def test_jsonrpc_error() -> None:
    r = jsonrpc_error(-32600, "Invalid request", request_id=1)
    assert r["error"]["code"] == -32600
    assert r["error"]["message"] == "Invalid request"


# ----- message_adapter -----


def test_message_parts_to_user_input_text_only() -> None:
    parts = [{"type": "text", "text": "Hello"}]
    assert message_parts_to_user_input(parts) == "Hello"


def test_message_parts_to_user_input_file_summary() -> None:
    parts = [{"type": "file", "filename": "x.pdf"}]
    assert "[Attachment: x.pdf]" in message_parts_to_user_input(parts)


def test_message_parts_to_user_input_and_attachments_inline() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        parts = [
            {"type": "text", "text": "See file"},
            {
                "type": "file",
                "filename": "a.txt",
                "mimeType": "text/plain",
                "inlineData": {"data": base64.b64encode(b"content").decode()},
            },
        ]
        user_input, attachments = message_parts_to_user_input_and_attachments(
            parts, workspace_dir=tmp
        )
        assert "See file" in user_input
        assert len(attachments) == 1
        assert attachments[0]["filename"] == "a.txt"
        assert Path(attachments[0]["path"]).read_text() == "content"


def test_message_parts_to_message_promotes_image_file_to_attachment() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        parts = [
            {"type": "text", "text": "Look at this"},
            {
                "type": "file",
                "filename": "photo.png",
                "mimeType": "image/png",
                "inlineData": {"data": base64.b64encode(b"pngdata").decode()},
            },
        ]
        message = message_parts_to_message(parts, workspace_dir=tmp, metadata={"conversation_id": "c1"})
        assert message.role == MessageRole.USER
        assert message.kind == MessageKind.CHAT
        assert message.text == "Look at this"
        assert len(message.attachments) == 1
        assert message.attachments[0].kind == AttachmentKind.IMAGE
        assert message.attachments[0].filename == "photo.png"
        assert message.metadata["conversation_id"] == "c1"
        assert "a2a_attachments" in message.metadata


def test_message_parts_to_message_text_only_does_not_create_attachment_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        message = message_parts_to_message(
            [{"type": "text", "text": "plain text only"}],
            workspace_dir=tmp,
        )

        assert message.text == "plain text only"
        assert message.attachments == []
        assert not (root / ".a2a_attachments").exists()


def test_run_result_to_artifact_parts_text_only() -> None:
    result = RunResult(success=True, output="done")
    parts = run_result_to_artifact_parts(result)
    assert len(parts) == 1
    assert parts[0]["type"] == "text"
    assert parts[0]["text"] == "done"


def test_run_result_to_artifact_parts_prefers_output_text() -> None:
    result = RunResult(
        success=True,
        output={"content": "[\"line1\\n\", \"line2\\n\"]"},
        output_text="line1\nline2\n",
    )
    parts = run_result_to_artifact_parts(result)
    assert len(parts) == 1
    assert parts[0]["type"] == "text"
    assert parts[0]["text"] == "line1\nline2"


def test_run_result_to_artifact_parts_with_a2a_output_files() -> None:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"file content")
        f.flush()
        path = f.name
    try:
        result = RunResult(
            success=True,
            output="done",
            metadata={"a2a_output_files": [path]},
        )
        parts = run_result_to_artifact_parts(result)
        assert len(parts) >= 1
        text_parts = [p for p in parts if p.get("type") == "text"]
        file_parts = [p for p in parts if p.get("type") == "file"]
        assert any(p.get("text") == "done" for p in text_parts)
        assert len(file_parts) == 1
        assert file_parts[0].get("inlineData", {}).get("data") == base64.b64encode(b"file content").decode()
    finally:
        Path(path).unlink()


def test_run_result_to_artifact_dict() -> None:
    result = RunResult(success=True, output="ok")
    art = run_result_to_artifact_dict(result, artifact_id="aid", name="out")
    assert art["artifactId"] == "aid"
    assert art["name"] == "out"
    assert len(art["parts"]) == 1


# ----- handlers (async via asyncio.run) -----


def test_dispatch_request_tasks_send() -> None:
    import asyncio
    from dare_framework.a2a.server.handlers import dispatch_request
    from dare_framework.context import Message

    async def mock_run(task: Message) -> RunResult:
        assert isinstance(task, Message)
        assert task.role == MessageRole.USER
        assert task.kind == MessageKind.CHAT
        assert task.text == "Hi"
        return RunResult(success=True, output="hello")

    async def run() -> None:
        store: dict[str, object] = {}
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/send",
            "params": {
                "id": "t1",
                "message": {"role": "user", "parts": [{"type": "text", "text": "Hi"}]},
            },
        }
        resp = await dispatch_request(req, mock_run, store)
        assert resp.get("id") == 1
        assert "result" in resp
        result = resp["result"]
        assert result["id"] == "t1"
        assert result["status"]["state"] == "completed"
        assert "artifacts" in result
        assert store.get("t1") == result

    asyncio.run(run())


def test_dispatch_request_tasks_get() -> None:
    import asyncio
    from dare_framework.a2a.server.handlers import dispatch_request

    async def run() -> None:
        store = {"t1": {"id": "t1", "status": {"state": "completed"}}}
        req = {"jsonrpc": "2.0", "id": 2, "method": "tasks/get", "params": {"id": "t1"}}
        resp = await dispatch_request(req, None, store)
        assert resp["result"]["id"] == "t1"

    asyncio.run(run())


def test_dispatch_request_method_not_found() -> None:
    import asyncio
    from dare_framework.a2a.server.handlers import dispatch_request

    async def run() -> None:
        req = {"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}}
        resp = await dispatch_request(req, None, {})
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    asyncio.run(run())
