from __future__ import annotations

import json
from pathlib import Path

import pytest

from dare_framework.config import Config
from dare_framework.context import AttachmentKind, AttachmentRef, Message
from dare_framework.hook.types import HookPhase
from dare_framework.model.types import ModelInput
from dare_framework.observability._internal.llm_io_capture_hook import (
    LLMIOCaptureHook,
    create_default_llm_io_capture_hook,
    summarize_llm_io_trace,
)


@pytest.mark.asyncio
async def test_llm_io_capture_hook_writes_jsonl_and_summary(tmp_path: Path) -> None:
    hook = LLMIOCaptureHook(base_dir=tmp_path)
    run_id = "run-123"
    model_input = ModelInput(
        messages=[Message(role="user", text="hello")],
        tools=[],
        metadata={"source": "unit-test"},
    )

    await hook.invoke(
        HookPhase.BEFORE_MODEL,
        payload={
            "run_id": run_id,
            "task_id": "task-1",
            "context_id": "ctx-1",
            "iteration": 1,
            "model_name": "mock-model",
            "model_input": model_input,
        },
    )
    await hook.invoke(
        HookPhase.AFTER_MODEL,
        payload={
            "run_id": run_id,
            "iteration": 1,
            "model_usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
            "duration_ms": 12.5,
            "model_output": {
                "content": "world",
                "tool_calls": [],
            },
        },
    )

    trace_path = tmp_path / "run-123.llm_io.jsonl"
    assert trace_path.exists()
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["run_id"] == "run-123"
    assert record["iteration"] == 1
    assert record["model_name"] == "mock-model"
    assert record["request"]["messages"][0]["text"] == "hello"
    assert record["response"]["content"] == "world"
    assert record["usage"]["total_tokens"] == 10

    summary = summarize_llm_io_trace(trace_path)
    assert summary["model_calls"] == 1
    assert summary["prompt_tokens"] == 7
    assert summary["completion_tokens"] == 3
    assert summary["total_tokens"] == 10


@pytest.mark.asyncio
async def test_llm_io_capture_hook_groups_records_by_conversation_id(tmp_path: Path) -> None:
    hook = LLMIOCaptureHook(base_dir=tmp_path)
    first_input = ModelInput(
        messages=[Message(role="user", text="hello")],
        tools=[],
        metadata={},
    )
    second_input = ModelInput(
        messages=[Message(role="user", text="who are you")],
        tools=[],
        metadata={},
    )

    await hook.invoke(
        HookPhase.BEFORE_MODEL,
        payload={
            "run_id": "run-1",
            "conversation_id": "session-a",
            "iteration": 1,
            "model_name": "mock-model",
            "model_input": first_input,
        },
    )
    await hook.invoke(
        HookPhase.AFTER_MODEL,
        payload={
            "run_id": "run-1",
            "conversation_id": "session-a",
            "iteration": 1,
            "model_usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            "duration_ms": 10.0,
            "model_output": {
                "content": "hi",
                "tool_calls": [],
            },
        },
    )

    await hook.invoke(
        HookPhase.BEFORE_MODEL,
        payload={
            "run_id": "run-2",
            "conversation_id": "session-a",
            "iteration": 1,
            "model_name": "mock-model",
            "model_input": second_input,
        },
    )
    await hook.invoke(
        HookPhase.AFTER_MODEL,
        payload={
            "run_id": "run-2",
            "conversation_id": "session-a",
            "iteration": 1,
            "model_usage": {"prompt_tokens": 6, "completion_tokens": 3, "total_tokens": 9},
            "duration_ms": 11.0,
            "model_output": {
                "content": "I am assistant",
                "tool_calls": [],
            },
        },
    )

    trace_path = tmp_path / "session-a.llm_io.jsonl"
    assert trace_path.exists()
    records = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 2
    assert records[0]["run_id"] == "run-1"
    assert records[1]["run_id"] == "run-2"
    assert records[0]["conversation_id"] == "session-a"
    assert records[1]["conversation_id"] == "session-a"


def test_create_default_llm_io_capture_hook_uses_observability_config(tmp_path: Path) -> None:
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "observability": {
                "capture_content": True,
            },
        }
    )

    hook = create_default_llm_io_capture_hook(config)
    assert hook is not None


@pytest.mark.asyncio
async def test_llm_io_capture_hook_records_text_attachments_and_data(tmp_path: Path) -> None:
    hook = LLMIOCaptureHook(base_dir=tmp_path)
    model_input = ModelInput(
        messages=[
            Message(
                role="user",
                kind="chat",
                text="describe image",
                attachments=[AttachmentRef(kind=AttachmentKind.IMAGE, uri="https://example.com/a.png")],
                data={"hint": "focus on charts"},
            )
        ],
        tools=[],
        metadata={},
    )

    await hook.invoke(
        HookPhase.BEFORE_MODEL,
        payload={
            "run_id": "run-typed",
            "iteration": 1,
            "model_name": "mock-model",
            "model_input": model_input,
        },
    )
    await hook.invoke(
        HookPhase.AFTER_MODEL,
        payload={
            "run_id": "run-typed",
            "iteration": 1,
            "model_usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "duration_ms": 1.0,
            "model_output": {"content": "ok", "tool_calls": []},
        },
    )

    record = json.loads((tmp_path / "run-typed.llm_io.jsonl").read_text(encoding="utf-8").splitlines()[0])
    message = record["request"]["messages"][0]
    assert message["text"] == "describe image"
    assert message["attachments"][0]["kind"] == "image"
    assert message["attachments"][0]["uri"] == "https://example.com/a.png"
    assert message["data"] == {"hint": "focus on charts"}
