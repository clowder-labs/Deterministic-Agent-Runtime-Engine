"""CLI command parsing and session state management."""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommandType(Enum):
    """CLI slash commands."""
    QUIT = "quit"
    MODE = "mode"
    APPROVE = "approve"
    REJECT = "reject"
    STATUS = "status"
    HELP = "help"


class ExecutionMode(Enum):
    """Execution modes."""
    PLAN = "plan"        # Generate plan → await approval → execute
    EXECUTE = "execute"  # Direct ReAct execution


class SessionStatus(Enum):
    """Session state."""
    IDLE = "idle"
    AWAITING_APPROVAL = "awaiting"
    RUNNING = "running"
    COMPLETED = "completed"


@dataclass
class Command:
    """Parsed command."""
    type: CommandType
    args: list[str]
    raw_input: str


@dataclass
class CLISessionState:
    """CLI session state (externalized from model memory)."""
    mode: ExecutionMode = ExecutionMode.EXECUTE  # Default: Execute mode (direct ReAct)
    status: SessionStatus = SessionStatus.IDLE
    pending_plan: Any | None = None
    pending_task_description: str | None = None

    def reset_task(self) -> None:
        """Clear task state, keep mode."""
        self.status = SessionStatus.IDLE
        self.pending_plan = None
        self.pending_task_description = None


def parse_command(user_input: str) -> Command | tuple[None, str]:
    """Parse user input into Command or return (None, task_description).

    Returns:
        Command if slash command detected
        (None, task_text) if regular input (to be executed as task)
    """
    stripped = user_input.strip()

    # Not a command - treat as task
    if not stripped.startswith("/"):
        return (None, stripped)

    # Parse command
    parts = stripped[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []

    # Map to CommandType
    command_map = {
        "quit": CommandType.QUIT,
        "exit": CommandType.QUIT,
        "q": CommandType.QUIT,
        "mode": CommandType.MODE,
        "approve": CommandType.APPROVE,
        "reject": CommandType.REJECT,
        "status": CommandType.STATUS,
        "help": CommandType.HELP,
    }

    if cmd_name not in command_map:
        return (None, stripped)  # Unknown command, treat as task

    return Command(
        type=command_map[cmd_name],
        args=args,
        raw_input=user_input
    )
