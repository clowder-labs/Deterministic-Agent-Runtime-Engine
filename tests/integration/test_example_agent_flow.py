import importlib.util
import sys
from pathlib import Path

import pytest

from dare_framework.models import PlanStep, new_id


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
        PlanStep(step_id=new_id("step"), tool_name="read_file", tool_input={"path": "sample.txt"})
    ]

    CodingAgent = _load_coding_agent()
    agent = CodingAgent(
        workspace=str(tmp_path),
        mock_mode=True,
        plan_steps=plan_steps,
    )

    result = await agent.run(task="read sample file")
    assert result.success is True
    assert result.output
    assert result.session_summary is not None
    assert result.milestone_results[0].summary is not None
    assert result.output[0].output["content"] == "hello"
