import importlib.util
import sys
from pathlib import Path

import pytest

pytest.skip(
    "Legacy example-agent flow depends on archived builder/runtime components; "
    "port to canonical dare_framework once equivalent APIs exist.",
    allow_module_level=True,
)

from dare_framework.contracts.ids import generator_id
from dare_framework.plan.planning import ProposedStep


def _load_coding_agent():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "examples" / "coding-agent" / "agent.py"
    if str(module_path.parent) not in sys.path:
        sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location("coding_agent_example", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("Failed to load coding agent module")
    spec.loader.exec_module(module)
    return module.CodingAgent


@pytest.mark.asyncio
async def test_example_agent_deterministic_flow(tmp_path):
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")

    plan_steps = [
        ProposedStep(
            step_id=generator_id("step"),
            capability_id="tool:read_file",
            params={"path": "sample.txt"},
        )
    ]

    CodingAgent = _load_coding_agent()
    agent = CodingAgent(
        workspace=str(tmp_path),
        plan_steps=plan_steps,
    )

    result = await agent.run(task="read sample file")
    assert result.success is True
    assert result.output
    assert result.session_summary is not None
    assert result.milestone_results[0].summary is not None
    assert result.output[0].output["content"] == "hello"
