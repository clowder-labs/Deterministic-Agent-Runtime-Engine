from __future__ import annotations

from pathlib import Path
import sys

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "03-dare-coding-agent"
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
