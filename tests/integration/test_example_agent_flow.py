import importlib.util
import sys
from pathlib import Path

import pytest


def _load_tool_example():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "examples" / "base_tool" / "v4_tooling.py"
    if str(module_path.parent) not in sys.path:
        sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location("base_tool_example", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("Failed to load base tool module")
    spec.loader.exec_module(module)
    return module.run_read_file


@pytest.mark.asyncio
async def test_example_agent_deterministic_flow(tmp_path):
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")

    run_read_file = _load_tool_example()
    tool_defs, result = await run_read_file(str(tmp_path), "sample.txt")

    assert any(tool["function"]["name"] == "read_file" for tool in tool_defs)
    assert result.success is True
    assert result.output["content"] == "hello"
