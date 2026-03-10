from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from dare_framework.context import Message
from dare_framework.hook.types import HookDecision, HookPhase
from dare_framework.model.types import ModelInput


def _load_example_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[2]
    module_path = root / relative_path
    example_dir = module_path.parent
    if str(example_dir) not in sys.path:
        sys.path.insert(0, str(example_dir))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_examples_08_hook_governance_cli_parse_stats_command() -> None:
    module = _load_example_module(
        "examples_08_hook_governance_cli_parse",
        "examples/08-hook-governance/cli.py",
    )
    command = module.parse_command("/stats")
    assert isinstance(command, module.Command)
    assert command.type == module.CommandType.STATS


def test_examples_08_hook_governance_default_workspace_is_cwd() -> None:
    module = _load_example_module(
        "examples_08_hook_governance_cli_workspace_default",
        "examples/08-hook-governance/cli.py",
    )
    parser = module._build_parser()
    args = parser.parse_args([])
    assert args.workspace == str(Path.cwd())


@pytest.mark.asyncio
async def test_examples_08_hook_governance_hook_blocks_model_with_keyword() -> None:
    module = _load_example_module(
        "examples_08_hook_governance_cli_block",
        "examples/08-hook-governance/cli.py",
    )
    hook = module.GovernancePolicyHook()
    model_input = ModelInput(
        messages=[Message(role="user", text="#hook_block_model please stop")],
        tools=[],
        metadata={},
    )
    result = await hook.invoke(
        HookPhase.BEFORE_MODEL,
        payload={"model_input": model_input},
    )
    assert result.decision is HookDecision.BLOCK


@pytest.mark.asyncio
async def test_examples_08_hook_governance_hook_patches_user_message() -> None:
    module = _load_example_module(
        "examples_08_hook_governance_cli_patch",
        "examples/08-hook-governance/cli.py",
    )
    hook = module.GovernancePolicyHook()
    model_input = ModelInput(
        messages=[Message(role="user", text="hello world")],
        tools=[],
        metadata={},
    )
    result = await hook.invoke(
        HookPhase.BEFORE_MODEL,
        payload={"model_input": model_input},
    )
    assert result.decision is HookDecision.ALLOW
    assert isinstance(result.patch, dict)
    patched_input = result.patch["model_input"]
    assert isinstance(patched_input, ModelInput)
    assert (patched_input.messages[0].text or "").startswith("[hook patched]")


@pytest.mark.asyncio
async def test_examples_08_hook_governance_hook_tracks_before_tool_allow() -> None:
    module = _load_example_module(
        "examples_08_hook_governance_cli_tool_allow",
        "examples/08-hook-governance/cli.py",
    )
    hook = module.GovernancePolicyHook()
    result = await hook.invoke(
        HookPhase.BEFORE_TOOL,
        payload={"tool_name": "read_file"},
    )
    assert result.decision is HookDecision.ALLOW
    assert hook.tool_seen_count == 1
    assert hook.last_tool_name == "read_file"
