
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
