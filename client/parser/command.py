"""Slash-command parsing for interactive ``chat`` mode."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommandType(Enum):
    """Recognized slash commands in interactive shell mode."""

    QUIT = "quit"
    HELP = "help"
    STATUS = "status"
    MODE = "mode"
    APPROVE = "approve"
    REJECT = "reject"
    APPROVALS = "approvals"
    MCP = "mcp"
    TOOLS = "tools"
    SESSIONS = "sessions"
    SKILLS = "skills"
    CONFIG = "config"
    MODEL = "model"
    INTERRUPT = "interrupt"


@dataclass(frozen=True)
class Command:
    """Parsed slash command."""

    type: CommandType
    args: list[str]
    raw_input: str


def parse_command(user_input: str) -> Command | tuple[None, str]:
    """Parse slash command or return plain task text."""
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return (None, stripped)

    command_text = stripped[1:].strip()
    if not command_text:
        # Keep bare slash input recoverable instead of crashing command parsing.
        return (None, stripped)

    parts = command_text.split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []

    command_map: dict[str, CommandType] = {
        "quit": CommandType.QUIT,
        "exit": CommandType.QUIT,
        "q": CommandType.QUIT,
        "help": CommandType.HELP,
        "status": CommandType.STATUS,
        "mode": CommandType.MODE,
        "approve": CommandType.APPROVE,
        "reject": CommandType.REJECT,
        "approvals": CommandType.APPROVALS,
        "mcp": CommandType.MCP,
        "tools": CommandType.TOOLS,
        "sessions": CommandType.SESSIONS,
        "skills": CommandType.SKILLS,
        "config": CommandType.CONFIG,
        "model": CommandType.MODEL,
        "interrupt": CommandType.INTERRUPT,
    }
    command_type = command_map.get(name)
    if command_type is None:
        # Keep unknown slash input as task text so users can still prompt with "/...".
        return (None, stripped)
    return Command(type=command_type, args=args, raw_input=user_input)
