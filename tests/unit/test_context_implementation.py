
import pytest
from dare_framework.config import Config
from dare_framework.context.context import Context
from dare_framework.context.types import Message, Budget
from dare_framework.model import Prompt
from dare_framework.tool._internal.tools.noop_tool import NoopTool
from dare_framework.tool.tool_manager import ToolManager

def test_context_initialization():
    config = Config()
    ctx = Context(id="test-id", config=config)
    assert ctx.id == "test-id"
    assert isinstance(ctx.budget, Budget)
    assert ctx.short_term_memory is not None
    assert ctx.long_term_memory is None
    assert ctx.knowledge is None
    assert ctx.config is config
    assert ctx.sys_prompt is None

def test_context_stm_methods():
    ctx = Context(config=Config())
    msg = Message(role="user", content="hello")
    ctx.stm_add(msg)
    
    messages = ctx.stm_get()
    assert len(messages) == 1
    assert messages[0].content == "hello"
    
    ctx.stm_clear()
    assert len(ctx.stm_get()) == 0

def test_context_budget_methods():
    ctx = Context(config=Config(), budget=Budget(max_tokens=100))
    ctx.budget_use("tokens", 50)
    assert ctx.budget.used_tokens == 50
    assert ctx.budget_remaining("tokens") == 50
    
    ctx.budget_check() # Should not raise
    
    ctx.budget_use("tokens", 60)
    with pytest.raises(RuntimeError, match="Token budget exceeded"):
        ctx.budget_check()

def test_context_assemble():
    prompt = Prompt(
        prompt_id="test.system",
        role="system",
        content="You are a helpful assistant",
        supported_models=["*"],
        order=0,
    )
    ctx = Context(config=Config(), sys_prompt=prompt)
    ctx.stm_add(Message(role="user", content="hi"))
    
    assembled = ctx.assemble()
    assert assembled.sys_prompt is not None
    assert assembled.sys_prompt.content == "You are a helpful assistant"
    assert len(assembled.messages) == 1
    assert assembled.messages[0].content == "hi"
    assert assembled.metadata["context_id"] == ctx.id


def test_context_requires_non_null_config():
    with pytest.raises(ValueError, match="non-null Config"):
        Context(id="missing-config", config=None)  # type: ignore[arg-type]


def test_context_list_tools_returns_capability_descriptors_from_tool_manager():
    manager = ToolManager(load_entrypoints=False)
    manager.register_tool(NoopTool())
    ctx = Context(config=Config(), tool_gateway=manager)

    tools = ctx.list_tools()

    assert len(tools) == 1
    assert tools[0].id == "noop"
    assert tools[0].name == "noop"


def test_context_exposes_public_tool_gateway_accessor_and_setter():
    manager = ToolManager(load_entrypoints=False)
    ctx = Context(config=Config())

    assert ctx.tool_gateway is None

    ctx.set_tool_gateway(manager)
    assert ctx.tool_gateway is manager


class _FakeRetrieval:
    def __init__(self, messages: list[Message], *, fail: bool = False) -> None:
        self._messages = list(messages)
        self._fail = fail
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, query: str = "", **kwargs: object) -> list[Message]:
        self.calls.append((query, dict(kwargs)))
        if self._fail:
            raise RuntimeError("retrieval failed")
        return list(self._messages)

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def clear(self) -> None:
        self._messages.clear()

    def compress(self, **kwargs: object) -> int:
        _ = kwargs
        return 0


def test_context_assemble_fuses_ltm_and_knowledge_with_latest_user_query():
    ltm = _FakeRetrieval([Message(role="assistant", content="ltm-hit")])
    knowledge = _FakeRetrieval([Message(role="assistant", content="knowledge-hit")])
    ctx = Context(
        config=Config(),
        long_term_memory=ltm,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", content="old request"))
    ctx.stm_add(Message(role="assistant", content="ack"))
    ctx.stm_add(Message(role="user", content="latest request"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["old request", "ack", "latest request", "ltm-hit", "knowledge-hit"]
    assert ltm.calls and ltm.calls[0][0] == "latest request"
    assert knowledge.calls and knowledge.calls[0][0] == "latest request"
    assert assembled.metadata["retrieval"]["ltm_count"] == 1
    assert assembled.metadata["retrieval"]["knowledge_count"] == 1
    assert assembled.metadata["retrieval"]["degraded"] is False


def test_context_assemble_degrades_when_token_budget_low():
    ltm = _FakeRetrieval([Message(role="assistant", content="ltm-hit")])
    knowledge = _FakeRetrieval([Message(role="assistant", content="knowledge-hit")])
    # Force a low remaining token budget so retrieval should be skipped.
    budget = Budget(max_tokens=32)
    ctx = Context(
        config=Config(),
        budget=budget,
        long_term_memory=ltm,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", content="x" * 160))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["x" * 160]
    assert assembled.metadata["retrieval"]["degraded"] is True
    assert assembled.metadata["retrieval"]["degrade_reason"] == "token_budget_low"


def test_context_assemble_handles_retrieval_exception_gracefully():
    ltm = _FakeRetrieval([Message(role="assistant", content="ltm-hit")], fail=True)
    knowledge = _FakeRetrieval([Message(role="assistant", content="knowledge-hit")])
    ctx = Context(
        config=Config(),
        long_term_memory=ltm,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", content="query"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["query", "knowledge-hit"]
    assert assembled.metadata["retrieval"]["degraded"] is True
    assert assembled.metadata["retrieval"]["degrade_reason"] == "ltm_retrieval_failed"


def test_context_assemble_single_source_uses_full_retrieval_budget():
    ltm = _FakeRetrieval([Message(role="assistant", content="x" * 64)])
    config = Config(
        long_term_memory={
            "assemble_top_k": 1,
            "assemble_reserve_tokens": 0,
            "assemble_ratio": 0.5,
        },
        knowledge={
            "assemble_top_k": 1,
            "assemble_ratio": 0.5,
        },
    )
    # Remaining retrieval budget ~= 40 tokens after STM estimate.
    ctx = Context(
        config=config,
        budget=Budget(max_tokens=49),
        long_term_memory=ltm,
        knowledge=None,
    )
    ctx.stm_add(Message(role="user", content="q"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["q", "x" * 64]
    assert assembled.metadata["retrieval"]["ltm_count"] == 1
    assert assembled.metadata["retrieval"]["degraded"] is False


def test_context_assemble_skips_oversized_retrieval_hits_and_keeps_later_candidates():
    ltm = _FakeRetrieval(
        [
            Message(role="assistant", content="x" * 220),
            Message(role="assistant", content="small-hit"),
        ]
    )
    config = Config(
        long_term_memory={
            "assemble_top_k": 2,
            "assemble_reserve_tokens": 0,
            "assemble_ratio": 1.0,
        },
        knowledge={
            "assemble_top_k": 0,
            "assemble_ratio": 0.0,
        },
    )
    ctx = Context(
        config=config,
        budget=Budget(max_tokens=35),
        long_term_memory=ltm,
        knowledge=None,
    )
    ctx.stm_add(Message(role="user", content="q"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["q", "small-hit"]
    assert assembled.metadata["retrieval"]["ltm_count"] == 1
    assert assembled.metadata["retrieval"]["degraded"] is True


def test_context_assemble_reserve_tokens_respects_knowledge_only_config():
    knowledge = _FakeRetrieval([Message(role="assistant", content="x" * 64)])
    config = Config(
        long_term_memory={"assemble_top_k": 0},
        knowledge={
            "assemble_top_k": 1,
            "assemble_ratio": 1.0,
            "assemble_reserve_tokens": 0,
        },
    )
    ctx = Context(
        config=config,
        budget=Budget(max_tokens=40),
        long_term_memory=None,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", content="q"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["q", "x" * 64]
    assert assembled.metadata["retrieval"]["knowledge_count"] == 1
    assert assembled.metadata["retrieval"]["degraded"] is False


def test_context_assemble_ignores_inactive_ltm_reserve_tokens_for_knowledge_only_retrieval():
    knowledge = _FakeRetrieval([Message(role="assistant", content="x" * 64)])
    config = Config(
        long_term_memory={
            "assemble_top_k": 0,
            "assemble_reserve_tokens": 10_000,
        },
        knowledge={
            "assemble_top_k": 1,
            "assemble_ratio": 1.0,
            "assemble_reserve_tokens": 0,
        },
    )
    ctx = Context(
        config=config,
        budget=Budget(max_tokens=40),
        long_term_memory=None,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", content="q"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["q", "x" * 64]
    assert assembled.metadata["retrieval"]["knowledge_count"] == 1
    assert assembled.metadata["retrieval"]["degraded"] is False


def test_context_assemble_rebalances_budget_when_ltm_retrieval_fails():
    ltm = _FakeRetrieval([Message(role="assistant", content="ltm-hit")], fail=True)
    knowledge = _FakeRetrieval([Message(role="assistant", content="x" * 64)])
    config = Config(
        long_term_memory={
            "assemble_top_k": 1,
            "assemble_ratio": 0.5,
            "assemble_reserve_tokens": 0,
        },
        knowledge={
            "assemble_top_k": 1,
            "assemble_ratio": 0.5,
            "assemble_reserve_tokens": 0,
        },
    )
    ctx = Context(
        config=config,
        budget=Budget(max_tokens=34),
        long_term_memory=ltm,
        knowledge=knowledge,
    )
    ctx.stm_add(Message(role="user", content="q"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["q", "x" * 64]
    assert assembled.metadata["retrieval"]["ltm_count"] == 0
    assert assembled.metadata["retrieval"]["knowledge_count"] == 1
    assert assembled.metadata["retrieval"]["degraded"] is True
    assert assembled.metadata["retrieval"]["degrade_reason"] == "ltm_retrieval_failed"


def test_context_assemble_handles_overflowing_numeric_retrieval_config() -> None:
    ltm = _FakeRetrieval([Message(role="assistant", content="ltm-hit")])
    config = Config(
        long_term_memory={
            "assemble_top_k": float("inf"),
            "assemble_reserve_tokens": float("inf"),
        },
        knowledge={"assemble_top_k": 0},
    )
    ctx = Context(
        config=config,
        long_term_memory=ltm,
        knowledge=None,
    )
    ctx.stm_add(Message(role="user", content="query"))

    assembled = ctx.assemble()

    assert assembled.metadata["retrieval"]["ltm_requested"] == 3


def test_context_assemble_rejects_infinite_ratio_and_keeps_budget_guardrails() -> None:
    ltm = _FakeRetrieval([Message(role="assistant", content="x" * 220)])
    config = Config(
        long_term_memory={
            "assemble_top_k": 1,
            "assemble_ratio": float("inf"),
            "assemble_reserve_tokens": 0,
        },
        knowledge={"assemble_top_k": 0},
    )
    ctx = Context(
        config=config,
        budget=Budget(max_tokens=40),
        long_term_memory=ltm,
        knowledge=None,
    )
    ctx.stm_add(Message(role="user", content="q"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["q"]
    assert assembled.metadata["retrieval"]["ltm_count"] == 0
    assert assembled.metadata["retrieval"]["degraded"] is True


def test_context_assemble_handles_overflowing_numeric_ratio_config() -> None:
    ltm = _FakeRetrieval([Message(role="assistant", content="ltm-hit")])
    config = Config(
        long_term_memory={
            "assemble_top_k": 1,
            "assemble_ratio": 10**10000,
            "assemble_reserve_tokens": 0,
        },
        knowledge={"assemble_top_k": 0},
    )
    ctx = Context(
        config=config,
        long_term_memory=ltm,
        knowledge=None,
    )
    ctx.stm_add(Message(role="user", content="query"))

    assembled = ctx.assemble()

    contents = [message.content for message in assembled.messages]
    assert contents == ["query", "ltm-hit"]
    assert assembled.metadata["retrieval"]["ltm_count"] == 1
