from __future__ import annotations

from pathlib import Path
import sys


def _resolve_example_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = (
        "05-dare-coding-agent-enhanced",
        "04-dare-coding-agent",
        "03-dare-coding-agent",
    )
    for candidate in candidates:
        path = root / "examples" / candidate
        if (path / "cli.py").exists():
            return path
    raise FileNotFoundError("Unable to locate examples/*/cli.py for coding-agent example tests.")


EXAMPLE_DIR = _resolve_example_dir()
sys.path.insert(0, str(EXAMPLE_DIR))

import cli  # type: ignore  # noqa: E402


def test_parse_command_mode_plan() -> None:
    command = cli.parse_command("/mode plan")
    assert isinstance(command, cli.Command)
    assert command.type == cli.CommandType.MODE
    assert command.args == ["plan"]


def test_parse_command_quit() -> None:
    command = cli.parse_command("/quit")
    assert isinstance(command, cli.Command)
    assert command.type == cli.CommandType.QUIT


def test_parse_command_task_text() -> None:
    command = cli.parse_command("build a demo")
    assert isinstance(command, tuple)
    assert command[0] is None
    assert command[1] == "build a demo"


def test_load_script_lines(tmp_path: Path) -> None:
    script = tmp_path / "demo.txt"
    script.write_text("""
# comment
/mode plan

Create a file
/approve
""", encoding="utf-8")

    lines = cli.load_script_lines(script)
    assert lines == ["/mode plan", "Create a file", "/approve"]
