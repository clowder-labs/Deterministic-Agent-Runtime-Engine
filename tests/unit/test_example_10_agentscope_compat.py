from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from dare_framework.config import Config
from dare_framework.context import Context, Message
from dare_framework.context.types import MessageKind, MessageRole
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse
from dare_framework.transport import AgentChannel, DirectClientChannel, EnvelopeKind, MessagePayload, TransportEnvelope, new_envelope_id


def _load_example_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "examples/10-agentscope-compat-single-agent/compat_agent.py"
    if not module_path.exists():
        raise AssertionError(f"expected example module to exist: {module_path}")
    spec = importlib.util.spec_from_file_location(
        "examples_10_agentscope_compat_agent",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["examples_10_agentscope_compat_agent"] = module
    spec.loader.exec_module(module)
    return module


def _load_example_cli_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "examples/10-agentscope-compat-single-agent/cli.py"
    if not module_path.exists():
        raise AssertionError(f"expected example cli module to exist: {module_path}")
    spec = importlib.util.spec_from_file_location(
        "examples_10_agentscope_compat_cli",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["examples_10_agentscope_compat_cli"] = module
    spec.loader.exec_module(module)
    return module


def _load_example_simple_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "examples/10-agentscope-compat-single-agent/simple_loop.py"
    if not module_path.exists():
        raise AssertionError(f"expected example simple module to exist: {module_path}")
    spec = importlib.util.spec_from_file_location(
        "examples_10_agentscope_simple_loop",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["examples_10_agentscope_simple_loop"] = module
    spec.loader.exec_module(module)
    return module


class _DeterministicCompatTestModel(IModelAdapter):
    """Deterministic ReAct model used only for test repeatability."""

    def __init__(self) -> None:
        self.called_tools: list[str] = []

    @property
    def name(self) -> str:
        return "deterministic-compat-test-model"

    @property
    def model(self) -> str:
        return "deterministic-compat-test-model"

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        _ = options
        used_tools = self._extract_called_tools(model_input.messages)
        self.called_tools = used_tools
        pending_tool = self._next_tool(used_tools)
        if pending_tool is not None:
            tool_name, arguments = pending_tool
            return ModelResponse(
                content=f"调用工具 {tool_name}",
                tool_calls=[
                    {
                        "id": f"call_{len(used_tools) + 1}",
                        "name": tool_name,
                        "arguments": arguments,
                    }
                ],
            )
        return ModelResponse(
            content=(
                "单 agent 演示完成：已依次执行 knowledge_get -> create_plan_notebook -> "
                "update_subtask_state -> finish_subtask -> echo。"
            ),
            tool_calls=[],
        )

    def _extract_called_tools(self, messages: list[Message]) -> list[str]:
        names: list[str] = []
        for message in messages:
            if message.role != "assistant":
                continue
            tool_calls = message.data.get("tool_calls", []) if isinstance(message.data, dict) else []
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                name = str(call.get("name", "")).strip()
                if name:
                    names.append(name)
        return names

    def _next_tool(self, used_tools: list[str]) -> tuple[str, dict[str, Any]] | None:
        pipeline: list[tuple[str, dict[str, Any]]] = [
            ("knowledge_get", {"query": "dare framework 等价能力", "top_k": 3}),
            (
                "create_plan_notebook",
                {
                    "name": "单代理验证计划",
                    "description": "验证等价能力",
                    "expected_outcome": "完成单代理替换验证",
                    "subtasks": [
                        {
                            "name": "验证工具链路",
                            "description": "执行核心工具和计划能力",
                            "expected_outcome": "工具链路可用",
                        }
                    ],
                },
            ),
            ("update_subtask_state", {"subtask_idx": 0, "state": "in_progress"}),
            ("finish_subtask", {"subtask_idx": 0, "subtask_outcome": "已完成链路验证"}),
            ("echo", {"text": "done"}),
        ]
        for name, arguments in pipeline:
            if name not in used_tools:
                return name, arguments
        return None


def _new_scripted_model() -> _DeterministicCompatTestModel:
    return _DeterministicCompatTestModel()


def test_example_10_cli_parse_response_uses_typed_summary_payload_for_errors() -> None:
    cli_module = _load_example_cli_module()
    success, text = cli_module._parse_response(  # type: ignore[attr-defined]
        TransportEnvelope(
            id="resp-error",
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id="msg-error",
                role=MessageRole.ASSISTANT,
                message_kind=MessageKind.SUMMARY,
                text="boom",
                data={"success": False, "code": "runtime_error", "reason": "boom"},
            ),
        )
    )
    assert success is False
    assert "boom" in text


class _DeterministicSimpleLoopModel(IModelAdapter):
    def __init__(self) -> None:
        self.called_tools: list[str] = []

    @property
    def name(self) -> str:
        return "deterministic-simple-loop-model"

    @property
    def model(self) -> str:
        return "deterministic-simple-loop-model"

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        _ = options
        used_tools: list[str] = []
        for message in model_input.messages:
            if message.role != "assistant":
                continue
            tool_calls = message.data.get("tool_calls", []) if isinstance(message.data, dict) else []
            for call in tool_calls:
                if isinstance(call, dict):
                    used_tools.append(str(call.get("name", "")))
        self.called_tools = used_tools
        if "execute_shell_command" not in used_tools:
            return ModelResponse(
                content="先执行命令",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "execute_shell_command",
                        "arguments": {"command": "echo simple-loop"},
                    }
                ],
            )
        return ModelResponse(content="simple loop done", tool_calls=[])


def test_compat_msg_roundtrip() -> None:
    module = _load_example_module()
    framework_msg = Message(role="user", text="hello", name="alice")
    compat = module.CompatMsg.from_framework_message(framework_msg)
    assert compat.blocks[0]["type"] == "text"
    assert compat.blocks[0]["text"] == "hello"

    restored = compat.to_framework_message()
    assert restored.role == "user"
    assert restored.name == "alice"
    assert restored.text == "hello"


def test_truncated_formatter_truncates_and_preserves_tool_pairs() -> None:
    module = _load_example_module()
    formatter = module.CompatTruncatedFormatter(max_chars=120)
    messages = [
        Message(role="system", text="system prompt"),
        Message(
            role="assistant",
            text="tool step",
            data={
                "tool_calls": [
                    {"id": "tc_1", "name": "demo_tool", "arguments": {"x": 1}},
                ]
            },
        ),
        Message(role="tool", name="tc_1", text='{"success": true, "output": "ok"}'),
        Message(role="user", text="x" * 220),
    ]

    formatted = formatter.format(messages)
    assert formatted.total_chars <= 120
    assert formatted.removed_count > 0

    tool_call_ids = set()
    tool_result_names = set()
    for item in formatted.messages:
        if item["role"] == "assistant":
            for call in item.get("metadata", {}).get("tool_calls", []):
                tool_call_ids.add(str(call.get("id", "")))
        if item["role"] == "tool":
            tool_result_names.add(str(item.get("name", "")))
    assert tool_result_names.issubset(tool_call_ids)


def test_json_session_bridge_roundtrip(tmp_path: Path) -> None:
    module = _load_example_module()
    notebook = module.CompatPlanNotebook()
    notebook.create_plan(
        name="p1",
        description="d1",
        expected_outcome="o1",
        subtasks=[
            {
                "name": "s1",
                "description": "do s1",
                "expected_outcome": "s1 done",
            }
        ],
    )
    notebook.update_subtask_state(0, "in_progress")

    context = Context(config=Config())
    context.stm_add(Message(role="user", text="first"))
    context.stm_add(Message(role="assistant", text="second"))

    session = module.JsonSessionBridge(save_dir=tmp_path)
    session_id = "session-example-10"
    session.save_session_state(
        session_id=session_id,
        context=context,
        notebook=notebook,
        user_id="u1",
    )

    context.stm_clear()
    notebook.clear()

    session.load_session_state(
        session_id=session_id,
        context=context,
        notebook=notebook,
        user_id="u1",
        allow_not_exist=False,
    )

    restored_messages = context.stm_get()
    assert [m.text for m in restored_messages] == ["first", "second"]
    assert notebook.current_plan is not None
    assert notebook.current_plan.subtasks[0].state == "in_progress"


def test_http_stateful_client_shim_metadata() -> None:
    module = _load_example_module()
    shim = module.HttpStatefulClientShim(
        name="demo",
        transport="streamable_http",
        url="http://127.0.0.1:8765/mcp",
    )
    assert shim.transport == "streamable_http"
    assert shim.is_connected is False
    assert shim.name == "demo"


@pytest.mark.asyncio
async def test_simple_loop_builder_runs_one_react_cycle(tmp_path: Path) -> None:
    module = _load_example_simple_module()
    test_model = _DeterministicSimpleLoopModel()
    agent = await module.build_simple_agent(
        workspace_dir=tmp_path,
        model_adapter=test_model,
    )
    result = await agent("run simple loop")
    assert result.success is True
    assert (result.output_text or "") == "simple loop done"
    assert "execute_shell_command" in test_model.called_tools


@pytest.mark.asyncio
async def test_single_agent_demo_flow_runs_with_equivalent_capabilities(
    tmp_path: Path,
) -> None:
    module = _load_example_module()
    test_model = _new_scripted_model()
    bundle = await module.build_single_agent_demo(
        workspace_dir=tmp_path,
        max_prompt_chars=5000,
        model_adapter=test_model,
    )

    result = await bundle.agent("请帮我做一个简短计划并给出结论。")
    assert result.success is True
    assert isinstance(result.output_text, str)
    assert "单 agent 演示完成" in result.output_text
    assert "knowledge_get" in test_model.called_tools
    assert "create_plan_notebook" in test_model.called_tools
    assert "finish_subtask" in test_model.called_tools

    assert bundle.notebook.current_plan is not None
    assert bundle.notebook.current_plan.subtasks[0].state == "done"


@pytest.mark.asyncio
async def test_single_agent_demo_transport_message_loop(tmp_path: Path) -> None:
    module = _load_example_module()
    client_channel = DirectClientChannel()
    channel = AgentChannel.build(client_channel)
    test_model = _new_scripted_model()
    bundle = await module.build_single_agent_demo(
        workspace_dir=tmp_path,
        max_prompt_chars=5000,
        agent_channel=channel,
        model_adapter=test_model,
    )

    await bundle.agent.start()
    try:
        response = await client_channel.ask(
            TransportEnvelope(
                id=new_envelope_id(),
                kind=EnvelopeKind.MESSAGE,
                payload=MessagePayload(
                    id=new_envelope_id(),
                    role=MessageRole.USER,
                    message_kind=MessageKind.CHAT,
                    text="请运行一次基础循环并返回结论。",
                ),
            ),
            timeout=30.0,
        )
    finally:
        await bundle.agent.stop()

    assert isinstance(response.payload, MessagePayload)
    payload = response.payload
    assert payload.message_kind is MessageKind.CHAT
    assert payload.data is not None
    assert payload.data.get("success") is True
    assert "单 agent 演示完成" in str(payload.data.get("output", ""))


@pytest.mark.asyncio
async def test_example_10_cli_script_mode_uses_transport(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_module = _load_example_cli_module()

    class _FakeOpenRouterModelAdapter(_DeterministicCompatTestModel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()
            self._model_name = str(kwargs.get("model", "fake-openrouter"))

        @property
        def model(self) -> str:
            return self._model_name

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(cli_module, "OpenRouterModelAdapter", _FakeOpenRouterModelAdapter)

    workspace = tmp_path / "workspace"
    script = tmp_path / "demo_script.txt"
    script.write_text(
        "\n".join(
            [
                "/status",
                "请执行一轮单 agent 兼容性验证。",
                "/save test-session",
                "/quit",
            ]
        ),
        encoding="utf-8",
    )

    await cli_module.main(
        [
            "--workspace",
            str(workspace),
            "--max-prompt-chars",
            "5000",
            "--model",
            "fake/test-model",
            "--script",
            str(script),
        ]
    )

    output = capsys.readouterr().out
    assert "model=fake/test-model" in output
    assert "status=running" in output
    assert "单 agent 演示完成" in output
    assert (workspace / "sessions" / "demo_test-session.json").exists()
