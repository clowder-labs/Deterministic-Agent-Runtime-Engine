import pytest

from dare_framework2.config import Config
from dare_framework2.tool.impl.edit_line_tool import EditLineTool
from dare_framework2.tool.impl.read_file_tool import ReadFileTool
from dare_framework2.tool.impl.search_code_tool import SearchCodeTool
from dare_framework2.tool.impl.write_file_tool import WriteFileTool
from dare_framework2.tool.types import RunContext


@pytest.mark.asyncio
async def test_read_file_rejects_paths_outside_workspace(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("data")

    config = Config.from_dict({"workspace_roots": [str(root)]})
    ctx = RunContext(deps=None, run_id="run", config=config)

    tool = ReadFileTool()
    result = await tool.execute({"path": "../outside.txt"}, ctx)

    assert result.success is False
    assert result.error == "PATH_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_read_file_enforces_max_bytes(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("abcdef")

    config = Config.from_dict(
        {
            "workspace_roots": [str(root)],
            "tools": {"read_file": {"max_bytes": 3}},
        }
    )
    ctx = RunContext(deps=None, run_id="run", config=config)

    tool = ReadFileTool()
    result = await tool.execute({"path": "sample.txt"}, ctx)

    assert result.success is False
    assert result.error == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_write_file_enforces_max_bytes(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    config = Config.from_dict(
        {
            "workspace_roots": [str(root)],
            "tools": {"write_file": {"max_bytes": 3}},
        }
    )
    ctx = RunContext(deps=None, run_id="run", config=config)

    tool = WriteFileTool()
    result = await tool.execute({"path": "out.txt", "content": "abcd"}, ctx)

    assert result.success is False
    assert result.error == "CONTENT_TOO_LARGE"


@pytest.mark.asyncio
async def test_search_code_orders_results_deterministically(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "b.py").write_text("match\n")
    (root / "a.py").write_text("match\nmatch\n")

    config = Config.from_dict({"workspace_roots": [str(root)]})
    ctx = RunContext(deps=None, run_id="run", config=config)

    tool = SearchCodeTool()
    result = await tool.execute({"pattern": "match"}, ctx)

    assert result.success is True
    matches = result.output["matches"]
    assert [(m["file"], m["line"]) for m in matches] == [
        ("a.py", 1),
        ("a.py", 2),
        ("b.py", 1),
    ]


@pytest.mark.asyncio
async def test_edit_line_strict_match_mismatch(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("one\ntwo\n")

    config = Config.from_dict({"workspace_roots": [str(root)]})
    ctx = RunContext(deps=None, run_id="run", config=config)

    tool = EditLineTool()
    result = await tool.execute(
        {"path": "sample.txt", "mode": "delete", "line_number": 2, "text": "nope"},
        ctx,
    )

    assert result.success is False
    assert result.error == "LINE_MISMATCH"
