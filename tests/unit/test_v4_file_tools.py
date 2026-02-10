import pytest

from dare_framework.tool._internal.tools import (
    EditLineTool,
    ReadFileTool,
    SearchCodeTool,
    WriteFileTool,
)
from dare_framework.tool.types import RunContext


@pytest.mark.asyncio
async def test_read_file_rejects_paths_outside_workspace(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("data")

    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = ReadFileTool()
    result = await tool.execute({"path": "../outside.txt"}, ctx)

    assert result.success is False
    assert result.output.get("code") == "PATH_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_read_file_enforces_max_bytes(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("abcdef")

    ctx = RunContext(
        deps=None,
        run_id="run",
        config={
            "workspace_roots": [str(root)],
            "tools": {"read_file": {"max_bytes": 3}},
        },
    )

    tool = ReadFileTool()
    result = await tool.execute({"path": "sample.txt"}, ctx)

    assert result.success is False
    assert result.output.get("code") == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_write_file_enforces_max_bytes(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    ctx = RunContext(
        deps=None,
        run_id="run",
        config={
            "workspace_roots": [str(root)],
            "tools": {"write_file": {"max_bytes": 3}},
        },
    )

    tool = WriteFileTool()
    result = await tool.execute({"path": "out.txt", "content": "abcd"}, ctx)

    assert result.success is False
    assert result.output.get("code") == "CONTENT_TOO_LARGE"


@pytest.mark.asyncio
async def test_search_code_orders_results_deterministically(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "b.py").write_text("match\n")
    (root / "a.py").write_text("match\nmatch\n")

    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = SearchCodeTool()
    result = await tool.execute({"pattern": "match"}, ctx)

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

    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = EditLineTool()
    result = await tool.execute(
        {"path": "sample.txt", "mode": "delete", "line_number": 2, "text": "nope"},
        ctx,
    )

    assert result.success is False
    assert result.output.get("code") == "LINE_MISMATCH"


@pytest.mark.asyncio
async def test_edit_line_insert_defaults_line_number_to_first_line(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("one\ntwo\n")

    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = EditLineTool()
    result = await tool.execute(
        {"path": "sample.txt", "mode": "insert", "text": "zero"},
        ctx,
    )

    assert result.success is True
    assert result.output["line_number"] == 1
    assert target.read_text() == "zero\none\ntwo\n"


@pytest.mark.asyncio
async def test_edit_line_rejects_explicit_null_line_number(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("one\ntwo\n")

    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = EditLineTool()
    result = await tool.execute(
        {"path": "sample.txt", "mode": "delete", "line_number": None},
        ctx,
    )

    assert result.success is False
    assert result.output.get("code") == "INVALID_LINE"
    assert target.read_text() == "one\ntwo\n"


@pytest.mark.asyncio
async def test_read_file_line_range_truncates(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("one\ntwo\nthree\n")

    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = ReadFileTool()
    result = await tool.execute({"path": "sample.txt", "start_line": 2, "end_line": 2}, ctx)

    assert result.success is True
    assert result.output["content"] == "two\n"
    assert result.output["truncated"] is True


@pytest.mark.asyncio
async def test_search_code_respects_max_results(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.py").write_text("match\nmatch\n")
    (root / "b.py").write_text("match\n")

    ctx = RunContext(
        deps=None,
        run_id="run",
        config={
            "workspace_roots": [str(root)],
            "tools": {"search_code": {"max_results": 2}},
        },
    )

    tool = SearchCodeTool()
    result = await tool.execute({"pattern": "match"}, ctx)

    assert result.success is True
    assert result.output["total_matches"] == 2
    assert result.output["truncated"] is True
