from __future__ import annotations

import pytest

from dare_framework.config import Config
from dare_framework.context.context import Context
from dare_framework.context.types import AttachmentKind, AttachmentRef, Budget, Message
from dare_framework.model import Prompt
from dare_framework.tool._internal.tools.noop_tool import NoopTool
from dare_framework.tool.tool_manager import ToolManager


def test_context_initialization() -> None:
    config = Config()
    ctx = Context(id="test-id", config=config)

    assert ctx.id == "test-id"
    assert isinstance(ctx.budget, Budget)
    assert ctx.short_term_memory is not None
    assert ctx.long_term_memory is None
    assert ctx.knowledge is None
    assert ctx.config is config
    assert ctx.sys_prompt is None


def test_context_stm_methods() -> None:
    ctx = Context(config=Config())
    msg = Message(role="user", text="hello")
    ctx.stm_add(msg)

    messages = ctx.stm_get()
    assert len(messages) == 1
    assert messages[0].text == "hello"

    ctx.stm_clear()
    assert len(ctx.stm_get()) == 0


def test_context_budget_methods() -> None:
    ctx = Context(config=Config(), budget=Budget(max_tokens=100))
    ctx.budget_use("tokens", 50)

    assert ctx.budget.used_tokens == 50
    assert ctx.budget_remaining("tokens") == 50

    ctx.budget_check()

    ctx.budget_use("tokens", 60)
    with pytest.raises(RuntimeError, match="Token budget exceeded"):
        ctx.budget_check()


def test_context_assemble() -> None:
    prompt = Prompt(
        prompt_id="test.system",
        role="system",
        content="You are a helpful assistant",
        supported_models=["*"],
        order=0,
    )
    ctx = Context(config=Config(), sys_prompt=prompt)
    ctx.stm_add(Message(role="user", text="hi"))

    assembled = ctx.assemble()

    assert assembled.sys_prompt is not None
    assert assembled.sys_prompt.content == "You are a helpful assistant"
    assert len(assembled.messages) == 1
    assert assembled.messages[0].text == "hi"
    assert assembled.metadata["context_id"] == ctx.id


def test_context_assemble_preserves_chat_attachments() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(
        Message(
            role="user",
            text="see image",
            attachments=[
                AttachmentRef(
                    kind=AttachmentKind.IMAGE,
                    uri="https://example.com/a.png",
                    mime_type="image/png",
                )
            ],
        )
    )

    assembled = ctx.assemble()

    assert len(assembled.messages) == 1
    assert assembled.messages[0].text == "see image"
    assert len(assembled.messages[0].attachments) == 1
    assert assembled.messages[0].attachments[0].uri == "https://example.com/a.png"


def test_context_requires_non_null_config() -> None:
    with pytest.raises(ValueError, match="non-null Config"):
        Context(id="missing-config", config=None)  # type: ignore[arg-type]


def test_context_list_tools_returns_capability_descriptors_from_tool_manager() -> None:
    manager = ToolManager(load_entrypoints=False)
    manager.register_tool(NoopTool())
    ctx = Context(config=Config(), tool_gateway=manager)

    tools = ctx.list_tools()

    assert len(tools) == 1
    assert tools[0].id == "noop"
    assert tools[0].name == "noop"


def test_context_exposes_public_tool_gateway_accessor_and_setter() -> None:
    manager = ToolManager(load_entrypoints=False)
    ctx = Context(config=Config())

    assert ctx.tool_gateway is None

    ctx.set_tool_gateway(manager)
    assert ctx.tool_gateway is manager


class _FakeRetrieval:
    def __init__(self, messages: list[Message]) -> None:
        self._messages = list(messages)
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, query: str = "", **kwargs: object) -> list[Message]:
        self.calls.append((query, dict(kwargs)))
        return list(self._messages)

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def clear(self) -> None:
        self._messages.clear()

    def compress(self, **kwargs: object) -> int:
        _ = kwargs
        return 0


def test_context_assemble_ignores_optional_retrieval_sources_in_default_strategy() -> None:
    ltm = _FakeRetrieval([Message(role="assistant", text="ltm-hit")])
    knowledge = _FakeRetrieval([Message(role="assistant", text="knowledge-hit")])
    ctx = Context(
        config=Config(),
        long_term_memory=ltm,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", text="latest request"))

    assembled = ctx.assemble()

    assert [message.text for message in assembled.messages] == ["latest request"]
    assert ltm.calls == []
    assert knowledge.calls == []
    assert assembled.metadata == {"context_id": ctx.id}


class _RecordingMovingCompressor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def prune(self, context: Context, **options: object) -> None:
        self.calls.append({"context": context, "options": dict(options)})


@pytest.mark.asyncio
async def test_context_compress_without_moving_compressor_is_noop() -> None:
    ctx = Context(config=Config())
    ctx.stm_add(Message(role="user", text="hello"))

    await ctx.compress(max_context_tokens=128)

    assert [message.text for message in ctx.stm_get()] == ["hello"]


@pytest.mark.asyncio
async def test_context_compress_uses_context_window_tokens_when_present() -> None:
    ctx = Context(config=Config(), context_window_tokens=256)
    compressor = _RecordingMovingCompressor()
    ctx.set_moving_compressor(compressor)

    await ctx.compress()

    assert len(compressor.calls) == 1
    assert compressor.calls[0]["context"] is ctx
    assert compressor.calls[0]["options"] == {"max_context_tokens": 256}


@pytest.mark.asyncio
async def test_context_compress_prefers_explicit_max_context_tokens() -> None:
    ctx = Context(config=Config(), context_window_tokens=256)
    compressor = _RecordingMovingCompressor()
    ctx.set_moving_compressor(compressor)

    await ctx.compress(max_context_tokens=64)

    assert len(compressor.calls) == 1
    assert compressor.calls[0]["options"] == {"max_context_tokens": 64}


@pytest.mark.asyncio
async def test_context_assemble_for_model_runs_moving_compressor_with_context_window_tokens() -> None:
    ctx = Context(config=Config(), context_window_tokens=256)
    compressor = _RecordingMovingCompressor()
    ctx.set_moving_compressor(compressor)
    ctx.stm_add(Message(role="user", text="query"))

    assembled = await ctx.assemble_for_model()

    assert len(compressor.calls) == 1
    assert compressor.calls[0]["context"] is ctx
    assert compressor.calls[0]["options"] == {"max_context_tokens": 256}
    assert [message.text for message in assembled.messages] == ["query"]
