from __future__ import annotations

import importlib
from dataclasses import dataclass

from dare_framework.config import Config
from dare_framework.context import AttachmentKind, AttachmentRef, Context, Message, MessageKind, MessageMark


def test_checkpoint_defaults_module_exports_are_importable() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")

    for symbol in (
        "MemoryCheckpointStore",
        "DefaultCheckpointSaveRestore",
        "StmContributor",
        "WorkspaceGitContributor",
        "SessionStateContributor",
        "SessionContextContributor",
    ):
        assert hasattr(defaults, symbol), f"missing checkpoint default symbol: {symbol}"


@dataclass
class _DummyConfig:
    model: str


@dataclass
class _DummySessionContext:
    session_id: str
    task_id: str
    config: _DummyConfig | None


@dataclass
class _DummyCtx:
    session_context: _DummySessionContext | None


def test_session_context_contributor_preserves_serialized_config_dict() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")
    contributor = defaults.SessionContextContributor()
    ctx = _DummyCtx(
        session_context=_DummySessionContext(
            session_id="s-1",
            task_id="t-1",
            config=_DummyConfig(model="gpt-4.1"),
        )
    )

    payload = contributor.serialize(ctx)

    assert payload is not None
    assert payload["config"] == {"model": "gpt-4.1"}


def test_stm_contributor_roundtrip_uses_current_message_text_shape() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")
    contributor = defaults.StmContributor()

    source_context = Context(config=Config())
    source_context.stm_add(
        Message(role="user", text="hello", name="alice", metadata={"trace_id": "t-1"})
    )
    source_ctx = type("Ctx", (), {"context": source_context})()

    payload = contributor.serialize(source_ctx)

    restored_context = Context(config=Config())
    restored_ctx = type("Ctx", (), {"context": restored_context})()
    contributor.deserialize_and_apply(payload, restored_ctx)

    restored_messages = restored_context.stm_get()
    assert len(restored_messages) == 1
    assert restored_messages[0].text == "hello"
    assert restored_messages[0].name == "alice"
    assert restored_messages[0].metadata == {"trace_id": "t-1"}


def test_stm_contributor_roundtrip_preserves_typed_message_payloads() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")
    contributor = defaults.StmContributor()

    source_context = Context(config=Config())
    source_context.stm_add(
        Message(
            role="user",
            text="see attachment",
            attachments=[
                AttachmentRef(
                    kind=AttachmentKind.IMAGE,
                    uri="https://example.com/a.png",
                    metadata={"source": "camera"},
                )
            ],
            mark=MessageMark.PERSISTENT,
            id="user-1",
        )
    )
    source_context.stm_add(
        Message(
            role="assistant",
            kind=MessageKind.TOOL_CALL,
            text="",
            data={"tool_calls": [{"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}}]},
            mark=MessageMark.IMMUTABLE,
            id="assistant-1",
        )
    )
    source_ctx = type("Ctx", (), {"context": source_context})()

    payload = contributor.serialize(source_ctx)

    restored_context = Context(config=Config())
    restored_ctx = type("Ctx", (), {"context": restored_context})()
    contributor.deserialize_and_apply(payload, restored_ctx)

    restored_messages = restored_context.stm_get()
    assert len(restored_messages) == 2

    assert restored_messages[0].attachments[0].uri == "https://example.com/a.png"
    assert restored_messages[0].attachments[0].metadata == {"source": "camera"}
    assert restored_messages[0].mark == MessageMark.PERSISTENT
    assert restored_messages[0].id == "user-1"

    assert restored_messages[1].kind == MessageKind.TOOL_CALL
    assert restored_messages[1].data == {
        "tool_calls": [{"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}}]
    }
    assert restored_messages[1].mark == MessageMark.IMMUTABLE
    assert restored_messages[1].id == "assistant-1"


def test_checkpoint_save_snapshot_deep_copies_nested_message_metadata() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")
    store = defaults.MemoryCheckpointStore()
    saver = defaults.DefaultCheckpointSaveRestore(store, [defaults.StmContributor()])

    source_context = Context(config=Config())
    source_context.stm_add(
        Message(
            role="user",
            text="hello",
            metadata={"trace": {"step": 1}},
        )
    )
    source_ctx = type("Ctx", (), {"context": source_context})()
    scope = type(
        "Scope",
        (),
        {"keys_for_save": lambda self: ["stm"], "keys_for_restore": lambda self: ["stm"]},
    )()

    checkpoint_id = saver.save(scope, source_ctx)

    source_context.stm_get()[0].metadata["trace"]["step"] = 99

    restored_context = Context(config=Config())
    restored_ctx = type("Ctx", (), {"context": restored_context})()
    saver.restore(checkpoint_id, scope, restored_ctx)

    restored_messages = restored_context.stm_get()
    assert restored_messages[0].metadata == {"trace": {"step": 1}}


def test_checkpoint_store_get_returns_deep_copied_payloads() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")
    store = defaults.MemoryCheckpointStore()
    saver = defaults.DefaultCheckpointSaveRestore(store, [defaults.StmContributor()])

    source_context = Context(config=Config())
    source_context.stm_add(
        Message(
            role="user",
            text="hello",
            metadata={"trace": {"step": 1}},
        )
    )
    scope = type(
        "Scope",
        (),
        {"keys_for_save": lambda self: ["stm"], "keys_for_restore": lambda self: ["stm"]},
    )()
    source_ctx = type("Ctx", (), {"context": source_context})()

    checkpoint_id = saver.save(scope, source_ctx)

    restored_context_a = Context(config=Config())
    restored_ctx_a = type("Ctx", (), {"context": restored_context_a})()
    saver.restore(checkpoint_id, scope, restored_ctx_a)
    restored_context_a.stm_get()[0].metadata["trace"]["step"] = 77

    restored_context_b = Context(config=Config())
    restored_ctx_b = type("Ctx", (), {"context": restored_context_b})()
    saver.restore(checkpoint_id, scope, restored_ctx_b)

    assert restored_context_b.stm_get()[0].metadata == {"trace": {"step": 1}}
