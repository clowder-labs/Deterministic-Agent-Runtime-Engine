import pytest

from dare_framework.tool._internal.tools import (
    EditLineTool,
    ReadFileTool,
    RunCommandTool,
    RunCmdTool,
    ReadCodeTool,
    SearchCodeTool,
    SearchFileTool,
    WriteCodeTool,
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
    result = await tool.execute(run_context=ctx, path="../outside.txt")

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
    result = await tool.execute(run_context=ctx, path="sample.txt")

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
    result = await tool.execute(run_context=ctx, path="out.txt", content="abcd")

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
    result = await tool.execute(run_context=ctx, pattern="match")

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
        run_context=ctx,
        path="sample.txt",
        mode="delete",
        line_number=2,
        text="nope",
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
        run_context=ctx,
        path="sample.txt",
        mode="insert",
        text="zero",
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
        run_context=ctx,
        path="sample.txt",
        mode="delete",
        line_number=None,
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
    result = await tool.execute(run_context=ctx, path="sample.txt", start_line=2, end_line=2)

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
    result = await tool.execute(run_context=ctx, pattern="match")

    assert result.success is True
    assert result.output["total_matches"] == 2
    assert result.output["truncated"] is True


@pytest.mark.asyncio
async def test_run_command_rejects_missing_cwd(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    missing = root / "missing-dir"
    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = RunCommandTool()
    result = await tool.execute({"command": "pwd", "cwd": str(missing)}, ctx)

    assert result.success is False
    assert result.output.get("code") == "INVALID_CWD"


@pytest.mark.asyncio
async def test_run_command_truncates_large_output(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ctx = RunContext(
        deps=None,
        run_id="run",
        config={
            "workspace_roots": [str(root)],
            "tools": {"run_command": {"max_output_bytes": 32}},
        },
    )

    tool = RunCommandTool()
    result = await tool.execute(
        {"command": "printf 'abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz'"},
        ctx,
    )

    assert result.success is True
    assert len(result.output["stdout"].encode("utf-8")) <= 32
    assert result.output["stdout_truncated"] is True
    assert result.output["stderr_truncated"] is False


@pytest.mark.asyncio
async def test_run_cmd_alias_executes_command(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = RunCmdTool()
    result = await tool.execute({"command": "printf 'ok'"}, ctx)

    assert result.success is True
    assert result.output["stdout"] == "ok"


@pytest.mark.asyncio
async def test_read_code_alias_reads_line_range(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "sample.py"
    target.write_text("a\nb\nc\n")
    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = ReadCodeTool()
    result = await tool.execute({"path": "sample.py", "start_line": 2, "end_line": 2}, ctx)

    assert result.success is True
    assert result.output["content"] == "b\n"


@pytest.mark.asyncio
async def test_write_code_alias_writes_file(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = WriteCodeTool()
    result = await tool.execute({"path": "main.py", "content": "print('x')\n"}, ctx)

    assert result.success is True
    assert (root / "main.py").read_text() == "print('x')\n"


@pytest.mark.asyncio
async def test_search_file_finds_matching_paths(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.py").write_text("x\n")
    (root / "b.txt").write_text("x\n")
    nested = root / "pkg"
    nested.mkdir()
    (nested / "c.py").write_text("x\n")
    ctx = RunContext(deps=None, run_id="run", config={"workspace_roots": [str(root)]})

    tool = SearchFileTool()
    result = await tool.execute({"path": ".", "pattern": "*.py"}, ctx)

    assert result.success is True
    assert result.output["paths"] == ["a.py", "pkg/c.py"]
